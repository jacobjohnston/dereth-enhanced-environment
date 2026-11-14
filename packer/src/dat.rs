//! The dat container a packed pack is written into, written as Pyreal's `pyreal-dat` writes one
//! (`write.rs`, `container.rs`, `layout.rs`, `btree.rs`), in the `client_*.dat` layout and held in
//! memory, with only what packing needs: a new container, records added to it, and a record read
//! back for `--check`.
//!
//! Blocks of the header's block size run from `0x400`, each starting with a link to the next.
//! Allocation is FIFO off the free list, the directory is an order-62 B-tree split top-down (30 /
//! 1 / 30) on the way down, and the room check grows the file by 1 MB at a time while it has no
//! more than `0x33` free blocks beyond what the record needs.

use sha2::{Digest, Sha256};

use crate::manifest::DataId;

/// The SHA-256 of a record's bytes.
#[must_use]
pub fn record_hash(bytes: &[u8]) -> [u8; 32] {
    Sha256::digest(bytes).into()
}

/// `DATFILE_TYPE`, the header's data set: the portal file's.
pub const PORTAL_DATFILE: u32 = 1;

/// A directory node: its 62 child links, its entry count and 61 entries of 24 bytes.
pub const NODE_SIZE: usize = 62 * 4 + 4 + 61 * 24;

/// The first block, after the prologue.
const FIRST_BLOCK: u32 = 0x400;
/// A node's entry count may not exceed this.
const MAX_ENTRIES: usize = 61;
/// A node's child links: the tree's fan-out.
const FAN_OUT: usize = 62;
/// Each half of a split keeps this many entries, with one entry promoted between them.
const SPLIT_HALF: usize = 30;
const COUNT_OFFSET: usize = FAN_OUT * 4;
const ENTRIES_OFFSET: usize = COUNT_OFFSET + 4;
/// An entry's length.
const ENTRY_BYTES: usize = 24;
/// Bit 31 of a block link: the block is on the free list.
const FREE_BIT: u32 = 0x8000_0000;
/// The journal's magic number, the `"PL"` in every journal record.
const TRANSACT_MAGIC: u32 = 0x0000_4C50;
/// The room check keeps this many blocks in hand above what the payload needs.
const ROOM_RESERVE: u32 = 0x33;
/// The room check grows the file by 1 MB at a time.
const EXPAND_BYTES: u32 = 0x0010_0000;
/// Where the header is, and its length.
const HEADER_AT: usize = 0x140;
const HEADER_BYTES: usize = 0x50;
/// Where the journal is.
const JOURNAL_AT: usize = 0x100;
/// The header's magic.
const HEADER_MAGIC: u32 = 0x5442;
/// The major version id as it appears in all four retail dats.
const VERSION_MAJOR: [u8; 16] = [
    0xD2, 0xD7, 0xA7, 0x34, 0x2F, 0x72, 0x46, 0x4C, 0x8A, 0xB4, 0xEF, 0x51, 0x4F, 0x85, 0x6F, 0xFD,
];

/// A directory entry: version flags, id, first block, length, date and iteration.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct Entry {
    bits: u32,
    id: u32,
    offset: u32,
    size: u32,
    date: u32,
    iteration: u32,
}

/// A directory node kept as its bytes.
#[derive(Debug, Clone)]
struct RawNode {
    bytes: Vec<u8>,
}

impl RawNode {
    fn empty() -> Self {
        Self {
            bytes: vec![0u8; NODE_SIZE],
        }
    }

    fn dword(&self, off: usize) -> u32 {
        u32::from_le_bytes([
            self.bytes[off],
            self.bytes[off + 1],
            self.bytes[off + 2],
            self.bytes[off + 3],
        ])
    }

    fn set_dword(&mut self, off: usize, v: u32) {
        self.bytes[off..off + 4].copy_from_slice(&v.to_le_bytes());
    }

    fn child(&self, i: usize) -> u32 {
        self.dword(i * 4)
    }

    fn set_child(&mut self, i: usize, v: u32) {
        self.set_dword(i * 4, v);
    }

    /// A first child link of 0 marks a leaf.
    fn is_leaf(&self) -> bool {
        self.child(0) == 0
    }

    fn num_entries(&self, offset: u32) -> Result<usize, String> {
        let n = self.dword(COUNT_OFFSET);
        if n as usize > MAX_ENTRIES {
            return Err(format!("the node at {offset:#X} holds {n} entries"));
        }
        Ok(n as usize)
    }

    fn set_num_entries(&mut self, n: usize) {
        #[allow(clippy::cast_possible_truncation)]
        self.set_dword(COUNT_OFFSET, n as u32);
    }

    fn entry(&self, i: usize) -> Entry {
        let o = ENTRIES_OFFSET + i * ENTRY_BYTES;
        let w = |k: usize| self.dword(o + k * 4);
        Entry {
            bits: w(0),
            id: w(1),
            offset: w(2),
            size: w(3),
            date: w(4),
            iteration: w(5),
        }
    }

    fn set_entry(&mut self, i: usize, e: Entry) {
        let o = ENTRIES_OFFSET + i * ENTRY_BYTES;
        for (k, v) in [e.bits, e.id, e.offset, e.size, e.date, e.iteration]
            .into_iter()
            .enumerate()
        {
            self.set_dword(o + k * 4, v);
        }
    }

    /// Entry `dst` = entry `src`, a whole-entry copy.
    fn move_entry(&mut self, dst: usize, src: usize) {
        let s = ENTRIES_OFFSET + src * ENTRY_BYTES;
        let d = ENTRIES_OFFSET + dst * ENTRY_BYTES;
        self.bytes.copy_within(s..s + ENTRY_BYTES, d);
    }
}

/// The header's fields a write changes, and the rest kept as bytes.
#[derive(Debug, Clone, Copy)]
struct Header {
    block_size: u32,
    file_size: u32,
    data_subset: u32,
    free_head: u32,
    free_tail: u32,
    free_count: u32,
    btree_root: u32,
}

impl Header {
    fn payload_per_block(&self) -> usize {
        self.block_size as usize - 4
    }
}

/// A container held in memory, open for writing and reading.
#[derive(Debug)]
pub struct Container<'s> {
    file: &'s mut Vec<u8>,
    raw_header: Vec<u8>,
    header: Header,
}

impl<'s> Container<'s> {
    /// A new container in `storage`, `file_size` bytes of `block_size`-byte blocks after the
    /// 0x400-byte prologue, all free but the directory's root, with the header retail's files
    /// carry.
    ///
    /// # Errors
    /// A block size or file size retail's file creation could not have made.
    pub fn create(
        storage: &'s mut Vec<u8>,
        block_size: u32,
        data_set: u32,
        data_subset: u32,
        file_size: u32,
    ) -> Result<Self, String> {
        if block_size < 8 || !block_size.is_multiple_of(4) {
            return Err(format!("block size {block_size}"));
        }
        if file_size <= FIRST_BLOCK
            || file_size > FREE_BIT
            || !(file_size - FIRST_BLOCK).is_multiple_of(block_size)
        {
            return Err(format!("file size {file_size} of blocks of {block_size}"));
        }
        let mut raw_header = vec![0u8; HEADER_BYTES];
        let mut put = |at: usize, v: u32| raw_header[at..at + 4].copy_from_slice(&v.to_le_bytes());
        put(0x00, HEADER_MAGIC);
        put(0x04, block_size);
        put(0x08, file_size);
        put(0x0C, data_set);
        put(0x10, data_subset);
        // The free list, the root, the LRU list, the master map and the game pack: none yet.
        put(0x34, 110);
        put(0x4C, 0x1A01);
        raw_header[0x3C..0x4C].copy_from_slice(&VERSION_MAJOR);
        let mut me = Self {
            file: storage,
            raw_header,
            header: Header {
                block_size,
                file_size,
                data_subset,
                free_head: 0,
                free_tail: 0,
                free_count: 0,
                btree_root: 0,
            },
        };
        // The 0x400-byte prologue: banner area, journal slot, header, tail padding.
        me.write_at(0, &[0u8; FIRST_BLOCK as usize]);
        me.clear_transaction();
        // One free block per block size, each linked to the next with bit 31, the last
        // terminated with `0x80000000`.
        let blocks = (file_size - FIRST_BLOCK) / block_size;
        me.header.free_count = blocks;
        me.header.free_head = FIRST_BLOCK;
        let mut block = vec![0u8; block_size as usize];
        let (mut cur, mut last) = (FIRST_BLOCK, FIRST_BLOCK);
        for _ in 0..blocks {
            last = cur;
            cur = last + block_size;
            block[..4].copy_from_slice(&(cur | FREE_BIT).to_le_bytes());
            me.write_at(last, &block);
        }
        me.header.free_tail = last;
        me.write_at(last, &FREE_BIT.to_le_bytes());
        me.header.file_size = cur;
        me.save_file_info();
        // The root node takes the first free block.
        let root = me.header.free_head;
        me.header.btree_root = root;
        me.store_data(&RawNode::empty().bytes, root)?;
        me.save_file_info();
        Ok(me)
    }

    /// The container already in `storage`, as written.
    ///
    /// # Errors
    /// It is not a container: no header, the wrong magic or block size.
    pub fn open(storage: &'s mut Vec<u8>) -> Result<Self, String> {
        let raw_header = storage
            .get(HEADER_AT..HEADER_AT + HEADER_BYTES)
            .ok_or("not a container")?
            .to_vec();
        let w = |i: usize| {
            u32::from_le_bytes([
                raw_header[i],
                raw_header[i + 1],
                raw_header[i + 2],
                raw_header[i + 3],
            ])
        };
        if w(0) != HEADER_MAGIC {
            return Err("not a container".into());
        }
        let block_size = w(0x04);
        if block_size < 8 || !block_size.is_multiple_of(4) {
            return Err(format!("block size {block_size}"));
        }
        let header = Header {
            block_size,
            file_size: w(0x08),
            data_subset: w(0x10),
            free_head: w(0x14),
            free_tail: w(0x18),
            free_count: w(0x1C),
            btree_root: w(0x20),
        };
        Ok(Self {
            file: storage,
            raw_header,
            header,
        })
    }

    /// The header's file size.
    #[must_use]
    pub fn file_size(&self) -> u32 {
        self.header.file_size
    }

    /// The header's data subset.
    #[must_use]
    pub fn data_subset(&self) -> u32 {
        self.header.data_subset
    }

    fn read_at(&self, offset: u32, buf: &mut [u8]) -> Result<(), String> {
        let start = offset as usize;
        let src = self
            .file
            .get(start..start + buf.len())
            .ok_or_else(|| format!("{offset:#X} is past the end"))?;
        buf.copy_from_slice(src);
        Ok(())
    }

    fn write_at(&mut self, offset: u32, buf: &[u8]) {
        let (start, end) = (offset as usize, offset as usize + buf.len());
        if self.file.len() < end {
            self.file.resize(end, 0);
        }
        self.file[start..end].copy_from_slice(buf);
    }

    fn check_block(&self, block: u32) -> Result<(), String> {
        if block < FIRST_BLOCK
            || block >= self.header.file_size
            || !(block - FIRST_BLOCK).is_multiple_of(self.header.block_size)
        {
            return Err(format!("block {block:#X} is out of range"));
        }
        Ok(())
    }

    fn link_at(&self, block: u32) -> Result<u32, String> {
        self.check_block(block)?;
        let mut b = [0u8; 4];
        self.read_at(block, &mut b)?;
        Ok(u32::from_le_bytes(b))
    }

    /// The header's five fields a write changes, written back.
    fn save_file_info(&mut self) {
        let h = self.header;
        let mut raw = std::mem::take(&mut self.raw_header);
        for (at, v) in [
            (0x08, h.file_size),
            (0x14, h.free_head),
            (0x18, h.free_tail),
            (0x1C, h.free_count),
            (0x20, h.btree_root),
        ] {
            raw[at..at + 4].copy_from_slice(&v.to_le_bytes());
        }
        #[allow(clippy::cast_possible_truncation)]
        self.write_at(HEADER_AT as u32, &raw);
        self.raw_header = raw;
    }

    /// A `NO_TRANS` record in the journal: five bytes.
    fn clear_transaction(&mut self) {
        let mut rec = [0u8; 5];
        rec[1..5].copy_from_slice(&TRANSACT_MAGIC.to_le_bytes());
        #[allow(clippy::cast_possible_truncation)]
        self.write_at(JOURNAL_AT as u32, &rec);
    }

    /// Store a payload as a block chain from `head`, the free-list head, taking the free list's
    /// next blocks in order; the header is written before the last block.
    fn store_data(&mut self, payload: &[u8], head: u32) -> Result<u32, String> {
        let per = self.header.payload_per_block();
        if payload.is_empty() {
            return Ok(0);
        }
        let exhausted = || "the free list ran out".to_owned();
        let mut remaining = payload.len();
        let mut src = 0usize;
        let mut dest = head;
        let mut taken: u32 = 1;
        let mut next = self.link_at(dest)? & !FREE_BIT;
        while remaining > 0 {
            let (link, chunk) = if per < remaining {
                if next == 0 {
                    return Err(exhausted());
                }
                let after = self.link_at(next)? & !FREE_BIT;
                taken += 1;
                let link = next;
                next = after;
                (link, per)
            } else {
                self.header.free_count = self
                    .header
                    .free_count
                    .checked_sub(taken)
                    .ok_or_else(exhausted)?;
                self.header.free_head = next;
                self.save_file_info();
                (0u32, remaining)
            };
            let mut block = Vec::with_capacity(chunk + 4);
            block.extend_from_slice(&link.to_le_bytes());
            block.extend_from_slice(&payload[src..src + chunk]);
            self.write_at(dest, &block);
            remaining -= chunk;
            src += chunk;
            dest = link;
        }
        Ok(taken)
    }

    /// The block chain from `offset`, `size` bytes of it.
    fn load_data(&self, mut offset: u32, size: usize) -> Result<Vec<u8>, String> {
        let per = self.header.payload_per_block();
        let block_size = self.header.block_size as usize;
        let blocks =
            (self.header.file_size as usize).saturating_sub(FIRST_BLOCK as usize) / block_size;
        if size > blocks * per {
            return Err(format!("a record of {size} bytes is larger than the file"));
        }
        let mut out = Vec::with_capacity(size);
        let mut remaining = size;
        let mut block = vec![0u8; block_size];
        while remaining > 0 && offset != 0 {
            let take = remaining.min(per);
            self.read_at(offset, &mut block[..take + 4])?;
            let link = u32::from_le_bytes([block[0], block[1], block[2], block[3]]);
            if link & FREE_BIT != 0 || link == offset {
                return Err(format!("the chain at {offset:#X} is broken"));
            }
            out.extend_from_slice(&block[4..take + 4]);
            remaining -= take;
            offset = link;
        }
        if remaining != 0 {
            return Err(format!("a chain is {remaining} bytes short"));
        }
        Ok(out)
    }

    /// Grow the file by whole blocks and link them onto the free tail.
    fn expand_file(&mut self, bytes: u32) -> Result<u32, String> {
        let bs = self.header.block_size;
        // No block may start at 2 GiB or past it: bit 31 of a link marks a free block.
        let room = FREE_BIT.saturating_sub(self.header.file_size) / bs;
        let n = (bytes / bs).min(room);
        if n == 0 {
            return Ok(0);
        }
        if self.header.free_tail == 0 {
            return Err("the free list ran out".into());
        }
        self.header.free_count += n;
        let mut cur = self.header.file_size;
        let mut last = cur;
        let mut block = vec![0u8; bs as usize];
        for _ in 0..n {
            last = cur;
            cur = last
                .checked_add(bs)
                .ok_or_else(|| "the file grew past 4 GiB".to_owned())?;
            block[..4].copy_from_slice(&(cur | FREE_BIT).to_le_bytes());
            self.write_at(last, &block);
        }
        let old_tail = self.header.free_tail;
        let first_new = self.header.file_size;
        self.write_at(last, &FREE_BIT.to_le_bytes());
        self.header.file_size = cur;
        self.header.free_tail = last;
        self.write_at(old_tail, &(first_new | FREE_BIT).to_le_bytes());
        self.save_file_info();
        Ok(n)
    }

    /// The room check: grow while no more than [`ROOM_RESERVE`] blocks beyond the payload's are
    /// free.
    fn check_room(&mut self, size: usize) -> Result<(), String> {
        #[allow(clippy::cast_possible_truncation)]
        let need = (size / self.header.payload_per_block()) as u32 + ROOM_RESERVE;
        while self.header.free_count <= need {
            if self.expand_file(EXPAND_BYTES)? == 0 {
                return Err(format!("the container is full at {}", self.header.file_size));
            }
        }
        Ok(())
    }

    fn read_node(&self, offset: u32) -> Result<RawNode, String> {
        self.check_block(offset)?;
        Ok(RawNode {
            bytes: self.load_data(offset, NODE_SIZE)?,
        })
    }

    /// Write a node back over its own chain, which is exactly a node long.
    fn write_node(&mut self, offset: u32, node: &RawNode) -> Result<(), String> {
        let per = self.header.payload_per_block();
        let want = NODE_SIZE.div_ceil(per);
        let wrong = || format!("the node at {offset:#X} is not {want} blocks long");
        let mut dest = offset;
        let mut src = 0usize;
        let mut used = 0usize;
        while src < NODE_SIZE {
            used += 1;
            if used > want {
                return Err(wrong());
            }
            let chunk = (NODE_SIZE - src).min(per);
            let link = if src + chunk >= NODE_SIZE {
                0
            } else {
                self.link_at(dest)?
            };
            if link & FREE_BIT != 0 || (link == 0 && src + chunk < NODE_SIZE) {
                return Err(wrong());
            }
            let mut buf = Vec::with_capacity(chunk + 4);
            buf.extend_from_slice(&link.to_le_bytes());
            buf.extend_from_slice(&node.bytes[src..src + chunk]);
            self.write_at(dest, &buf);
            src += chunk;
            dest = link;
        }
        if used != want {
            return Err(wrong());
        }
        Ok(())
    }

    /// Take the free-list head and store an empty node there.
    fn allocate_empty_node(&mut self) -> Result<u32, String> {
        let offset = self.header.free_head;
        self.check_block(offset)?;
        self.store_data(&RawNode::empty().bytes, offset)?;
        Ok(offset)
    }

    /// The entry for `id`: descend, then binary-search each node.
    fn find(&self, id: u32) -> Result<Option<Entry>, String> {
        if id == 0 {
            return Ok(None);
        }
        let mut offset = self.header.btree_root;
        loop {
            let node = self.read_node(offset)?;
            let n = node.num_entries(offset)?;
            let (mut lo, mut hi) = (0usize, n);
            while lo < hi {
                let mid = (lo + hi) / 2;
                let key = node.entry(mid).id;
                if key == id {
                    return Ok(Some(node.entry(mid)));
                } else if key < id {
                    lo = mid + 1;
                } else {
                    hi = mid;
                }
            }
            if node.is_leaf() {
                return Ok(None);
            }
            offset = node.child(lo);
        }
    }

    /// Split child `idx` of the node at `parent_offset`.
    fn split_child(&mut self, parent_offset: u32, idx: usize) -> Result<(), String> {
        let mut parent = self.read_node(parent_offset)?;
        let parent_n = parent.num_entries(parent_offset)?;
        let full_offset = parent.child(idx);
        let mut full = self.read_node(full_offset)?;
        if full.num_entries(full_offset)? != MAX_ENTRIES {
            return Err(format!("the node at {full_offset:#X} is split unfull"));
        }
        // The right half: entries 31..=60 and, for an internal node, child links 31..=61.
        let right_offset = self.allocate_empty_node()?;
        let mut right = RawNode::empty();
        for k in 0..SPLIT_HALF {
            right.set_entry(k, full.entry(SPLIT_HALF + 1 + k));
        }
        if !full.is_leaf() {
            for k in 0..=SPLIT_HALF {
                right.set_child(k, full.child(SPLIT_HALF + 1 + k));
            }
        }
        right.set_num_entries(SPLIT_HALF);
        self.write_node(right_offset, &right)?;
        // The parent gains entry 30 at `idx` and the new node as child `idx + 1`.
        let promoted = full.entry(SPLIT_HALF);
        for k in ((idx + 1)..=parent_n).rev() {
            parent.set_child(k + 1, parent.child(k));
            parent.move_entry(k, k - 1);
        }
        parent.set_child(idx + 1, right_offset);
        parent.set_entry(idx, promoted);
        parent.set_num_entries(parent_n + 1);
        self.write_node(parent_offset, &parent)?;
        // The left half keeps entries 0..=29; only its count is lowered.
        full.set_num_entries(SPLIT_HALF);
        self.write_node(full_offset, &full)
    }

    /// Insert a new entry, splitting full nodes on the way down.
    fn descend_to_add(&mut self, entry: Entry, payload: &[u8]) -> Result<(), String> {
        let id = entry.id;
        // Root split: a new root block pointing at the old one.
        let root_n = {
            let root = self.read_node(self.header.btree_root)?;
            root.num_entries(self.header.btree_root)?
        };
        if root_n == MAX_ENTRIES {
            let old_root = self.header.btree_root;
            let new_root = self.allocate_empty_node()?;
            let mut node = RawNode::empty();
            node.set_child(0, old_root);
            node.set_num_entries(0);
            self.header.btree_root = new_root;
            self.save_file_info();
            self.write_node(new_root, &node)?;
            self.split_child(new_root, 0)?;
        }
        let mut offset = self.header.btree_root;
        loop {
            let node = self.read_node(offset)?;
            let n = node.num_entries(offset)?;
            if node.is_leaf() {
                return self.insert_into_leaf(offset, node, n, entry, payload);
            }
            // The number of entries whose id is <= the target.
            let mut i = n;
            while i > 0 && node.entry(i - 1).id > id {
                i -= 1;
            }
            let child_offset = node.child(i);
            let child_n = {
                let child = self.read_node(child_offset)?;
                child.num_entries(child_offset)?
            };
            if child_n == MAX_ENTRIES {
                self.split_child(offset, i)?;
                let parent = self.read_node(offset)?;
                if parent.entry(i).id < id {
                    i += 1;
                }
                offset = parent.child(i);
            } else {
                offset = child_offset;
            }
        }
    }

    /// Shift the leaf's entries up, drop the new one in, store the payload at the free-list head,
    /// then write the node.
    fn insert_into_leaf(
        &mut self,
        offset: u32,
        mut node: RawNode,
        n: usize,
        entry: Entry,
        payload: &[u8],
    ) -> Result<(), String> {
        let mut i = n;
        while i > 0 && node.entry(i - 1).id > entry.id {
            node.move_entry(i, i - 1);
            i -= 1;
        }
        let head = self.header.free_head;
        #[allow(clippy::cast_possible_truncation)]
        let e = Entry {
            offset: head,
            size: payload.len() as u32,
            ..entry
        };
        node.set_entry(i, e);
        node.set_num_entries(n + 1);
        self.store_data(payload, head)?;
        self.write_node(offset, &node)
    }

    /// Add the record `id` holding `payload`, version 1, iteration 0 and no date.
    ///
    /// # Errors
    /// Id 0, an empty payload, an id already there, or a container that cannot hold it.
    pub fn save(&mut self, id: DataId, payload: &[u8]) -> Result<(), String> {
        if id.raw() == 0 || payload.is_empty() {
            return Err("no record 0, and no empty record".into());
        }
        #[allow(clippy::cast_possible_truncation)]
        let entry = Entry {
            bits: 1 << 16,
            id: id.raw(),
            offset: 0,
            size: payload.len() as u32,
            date: 0,
            iteration: 0,
        };
        self.check_room(payload.len())?;
        if self.find(id.raw())?.is_some() {
            return Err("saved twice".into());
        }
        self.descend_to_add(entry, payload)?;
        self.save_file_info();
        self.clear_transaction();
        Ok(())
    }

    /// The record `id`'s bytes.
    ///
    /// # Errors
    /// It is not there, or its chain will not read.
    pub fn read(&self, id: DataId) -> Result<Vec<u8>, String> {
        let entry = self
            .find(id.raw())?
            .ok_or_else(|| format!("no record {:#010X}", id.raw()))?;
        self.load_data(entry.offset, entry.size as usize)
    }
}
