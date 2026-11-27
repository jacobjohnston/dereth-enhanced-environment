# Enhanced Environment pack: reviewed and worked-on assets

Ledger of every asset in the art pack that has been worked on or reviewed, so later sessions don't redo it.
Built 2026-11-21 from pack main fbaee071 (version 0.5), the full commit history, the tables, the manifest and the
review notes and verdicts. Add to it as new rounds are reviewed.

Dates are the developer's local dates. "Card" is one entry on a review page. Ids are retail file ids; `0x05..` are
pictures, `0x01..`/`0x02..` models. A range such as `0x0500222A-223A` means every id from the first to the last.

## Counts

| Area | Worked on | Reviewed by the developer | Not reviewed or open |
|---|---|---|---|
| Trees and plants | 102 plant cards (90 still pack models in 0.5, 12 back on retail's model) plus 13 older-era plant models, 4 sway entries, 43 boulder models | 102 of 102 over 10 rounds (all passed by 2026-11-21); older plants over 3 checks | Boulders, ground cover, hay and ember beds never reviewed; older plants' last fix (018f49fe) not re-shown |
| Armour and clothing | 1,234 rows in `tables/armor.tsv` (1,233 armor.py materials) | Armour rounds 1-4 and clothing rounds 1-4 all good | Clothing round 5 (33 pictures) and the White Rabbit Mask rework: no verdict found |
| Props and items | Prop texture rounds 1-12: about 400 cards; relief kept to size, glaze, glass, crystal, metal, clear maps, the champagne painted anew, the hay heaps; iron doors, books, arms, chest, stone head and boulder, statue, torch pillars | All twelve prop rounds and their reworks, the red crystal obelisk's core and the bookshelves | Round 13 not started (after rank 943 in props.tsv) |
| Room and ground textures | 348 room materials in review set, ground round, dungeon rounds 27-30, sand, wall, floor and ceiling rounds 30-55 | Rounds 1-55 all good at the end: 449 of 667 prop-free End of Retail walls, floors and ceilings (98.5% of their drawn area) | Round 56 next; 106 automatic and 112 with no material; every other relief.py material is automatic and unreviewed |

Legend for verdict columns: `g` looks right, `r` needs work (note given), `u` shown and left unmarked,
blank not in that round, `s` shown in round 5 (that round was dropped, see below), `back` or `keep` is the developer's
keep pick (back to 0.4.4 model, or keep 0.4.45 model).

## 1. Trees and plants

Scope: the 102 pack `[[model]]` plants drawn in every era (`draws_on = "any"`), made by gen_pack.mjs (EZ-Tree),
shapes.mjs and cactus.py. Review page "Pack Trees Review", with a separate keep picks page. Each card: retail beside the pack at Holtburg; from round 6 also 0.4.4 and a red overlay of retail's shape.

### Rounds

| Round | Date | Cards | Result | Pack commit |
|---|---|---|---|---|
| Before | 2026-11-14 to 11-20 | all | 0.1 to 0.4.4 models; trunk-taper for 4BE and 12FF (c9bdec53) | v0.4.0, 141f440b (0.4.4) |
| 1 | 11-20 | 102 | 35 good, 24 needs work, 43 unmarked. Rule: good untouched; noted rebuilt; unmarked get EoR leaf colour and retail crown height; taller than retail is fine | eb36a304 |
| 2 | 11-20 | 67 | 30 good, 34 needs work, 3 unmarked | b7682e37 |
| 3 | 11-20 | 37 | 29 good, 8 needs work | ed253a2d |
| 4 | 11-20 | 8 | all good: every card passed at 0.4.45 | (then trunk fits efeeb015, f08e073c, 77171f64, e318f41e) |
| Keep picks | 11-21 | 65 | 26 back to 0.4.4 model, 39 keep 0.4.45 (12 with notes) | 9140bdef |
| 5 | 11-21 | 41 | roots-as-trunk (roots.py) shown; the developer rejected roots and all trunk fitting ("go back before we ever widened tree bases") | 380ac331, c5ff9f3c, then dropped in 22cb4085, d5a1b014 |
| 6 | 11-21 | 62 | 31 good, 31 needs work (sizes against retail, 0.4.4 returns) | 2d070e17 |
| 7 | 11-21 | 31 | 18 good, 13 needs work (match retail height, snowy back to 0.4.4) | c98a22b3 |
| 8 | 11-21 | 13 | all good; the developer asked for a build | c98a22b3 (tree-picks) |
| 9 | 11-21 | 2 | 4BE and 2D9 rolled back to 0.4.4, approved; yellow twin 12FF kept as is | 15ec42da (tree-rollback-044) |
| 10 | 11-21 | 1 | red birch 62B leaves back to 0.4.4's bright orange, approved | 703efe54 (tree-birch-044) |
| 0.5 | 11-21 | | squashed into a95f7082 | fbaee071 |
| Needle colour | 11-21 | 11 | Far crowns read near-black (the developer: "distant tree cards got a bit blobby"). Needles moved to a grey picture coloured as end of retail's crown, twice as bright; not yet shown to the developer | d723cadd, e9b788ec (fix/needle-colour) |
| Tree triangles | 11-22 | 22 | Same look with fewer triangles (`slim_trees.py`): every branch from half its rings; the conifers' middle level with one needle card for each crossed pair, grown 1.25; their far level without the branches the needles hide. Near levels and the round trees keep both cards of a pair, since one card alone showed thinner. About a third fewer triangles in view in a forest at Ultra. Not yet shown to the developer | ba69435d (review/tree-triangles) |
| Banyan trunks | 11-23 | 3 | 3ED, 3EE, 3EF: each stem, limb and root is now one smooth tube, so the bends show no lines (they were short separate tubes with a crack at every joint). Inner trunk slimmed to 55%, the developer's pick from mockups at 100%, 75% and 55%, so the stems round it are near its size; then the whole trunk, stems and inner trunk together, sized to retail's (about 3 m across at its foot, 2.2 m above), and the tree moved so the trunk stands where retail's does (0.4 m east, 0.59 m north of the middle). Height, spread and triangles unchanged | 35e3985c, fef8400f, 491444ba, 7df4ebdd (banyan-trunks) |
| Giant tree | 11-24 | 18 | End of Retail's trees and plants that reuse a pack model's parts under another id, found from a report of the giant tree at 0xBB80 (`twins.py`): 325 is the giant elm 251 at 1.5x; 3A1 the giant spruce 2DA in teal needles; F06, 2F1, 1C35, 1003, 1C3A, 7BE, 7DB, AC0, AC4, AC6, AC8 and AC9 as their twins. BAD and BAE are bare grey deadwood on End of Retail's record; A67 and F8E red-barked clump trees. Clump trees' trunk and first limb are one tube, with no crack at the fork (A35 too, on its first seed). The developer: keep. Braziers 104, 286, 287, 5B5, 625-62A wait on Pyreal's `lays_over` | d513391d, 54be21db, 25195ff4 (giant-tree) |

### Per tree

| Id | Name | Maker | R1 | R2 | R3 | R4 | Pick | R5 | R6 | R7 | R8 | R9-10 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0x02000258 | Large pine | EZ-Tree conifer | u | r | g |  | back | s | r | r | g |  |
| 0x02000257 | Young pine | EZ-Tree conifer | u | r | g |  | back | s | r | r | g |  |
| 0x02000256 | Middle pine | EZ-Tree conifer | u | r | g |  | back | s | r | r | g |  |
| 0x020002D3 | Tall spruce | EZ-Tree conifer | u | r | g |  | back | s | r | r | g |  |
| 0x020002D9 | Tall spruce, autumn | EZ-Tree conifer | u | r | g |  | back | s | r | r | g | g |
| 0x020002DA | Giant spruce, autumn | EZ-Tree conifer | u | g |  |  | back | s | r | r | g |  |
| 0x020002DB | Tall fir, teal | EZ-Tree conifer | u | r | g |  | back | s | r | r | g |  |
| 0x020002D8 | Fir, teal | EZ-Tree conifer | u | r | g |  | back | s | r | r | g |  |
| 0x02001C39 | Spruce pair | EZ-Tree conifer | u | r | g |  | keep | s | g |  |  |  |
| 0x0200129A | Redwood | EZ-Tree conifer | u | r | g |  | keep | s | g |  |  |  |
| 0x0200129B | Redwood, shorter | EZ-Tree conifer | u | r | g |  | keep | s | g |  |  |  |
| 0x020012FE | Young redwood | EZ-Tree conifer | u | r | g |  | keep | s | g |  |  |  |
| 0x020003A2 | Small pine, snowy | EZ-Tree conifer | u | r | g |  | keep | s | g |  |  |  |
| 0x020003A3 | Middle pine, snowy | EZ-Tree conifer | u | r | g |  | back | s | r | r | g |  |
| 0x020003A4 | Large pine, snowy | EZ-Tree conifer | u | r | g |  | back | s | r | r | g |  |
| 0x020003A7 | Tall spruce, snowy | EZ-Tree conifer | u | g |  |  | back | s | r | r | g |  |
| 0x020012FB | Spruce, snowy | EZ-Tree conifer | u | r | g |  | back | s | r | r | g |  |
| 0x02000246 | Small oak | EZ-Tree broadleaf | u | r | g |  | back | s | r | g |  |  |
| 0x02000240 | Oak sapling | EZ-Tree broadleaf | u | r | g |  | back | s | r | g |  |  |
| 0x0200062C | Birch | EZ-Tree broadleaf | u | r | g |  | back | s | g |  |  |  |
| 0x0200062B | Birch, red | EZ-Tree broadleaf | u | g |  |  | back | s | g |  |  | g |
| 0x020002F6 | Spreading bush | EZ-Tree broadleaf | u | r | r | g | back | s | g |  |  |  |
| 0x020004BE | Two-lobed ash | EZ-Tree broadleaf | r | g |  |  | back | s | g |  |  | g |
| 0x020012FF | Two-lobed ash, yellow | EZ-Tree broadleaf | r | g |  |  | back | s | g |  |  |  |
| 0x02000322 | Leafy oak | EZ-Tree broadleaf | r | r | g |  | keep | s | r | g |  |  |
| 0x020003EE | Banyan, tall | Banyan maker | g |  |  |  |  |  | r | g |  |  |
| 0x020003EF | Banyan | Banyan maker | g |  |  |  |  |  | r | r | g |  |
| 0x020003ED | Banyan, low | Banyan maker | g |  |  |  |  |  | r | g |  |  |
| 0x020007D4 | Great parasol tree | Parasol maker | r | g |  |  | back | s | r | g |  |  |
| 0x020007D9 | Bent parasol tree | Parasol maker | u | r | r | g | keep |  | g |  |  |  |
| 0x020003EB | Parasol tree | Parasol maker | u | r | g |  | keep |  | g |  |  |  |
| 0x020003EA | Parasol tree, larger | Parasol maker | u | r | r | g | keep |  | g |  |  |  |
| 0x020002D7 | Elm | Elm maker | u | g |  |  | back | s | r | g |  |  |
| 0x02000251 | Giant elm | Elm maker | u | r | g |  | back | s | r | g |  |  |
| 0x020002DC | Elm, slender | Elm maker | u | r | g |  | back | s | r | g |  |  |
| 0x020012FC | Crowned tree | Crowned tree maker | u | u | r | g | back | s | g |  |  |  |
| 0x020012FD | Crowned tree, tall | Crowned tree maker | u | g |  |  | back | s | g |  |  |  |
| 0x0200009D | Crowned tree, older weeping | Crowned tree maker | u | g |  |  |  |  | g |  |  |  |
| 0x02000A35 | Clump tree | Clump tree maker | u | g |  |  |  |  | g |  |  |  |
| 0x02000A38 | Stalk tree | Stalk tree maker | u | g |  |  | keep | s | g |  |  |  |
| 0x020010C7 | Wing tree | Wing tree maker | g |  |  |  |  |  | g |  |  |  |
| 0x020010CD | Wing tree, tall | Wing tree maker | g |  |  |  |  |  | g |  |  |  |
| 0x020010C5 | Puff tree | Puff tree maker | g |  |  |  |  |  | g |  |  |  |
| 0x020002F2 | Round shrub | Shrub maker | u | r | r | g | keep |  | g |  |  |  |
| 0x020002F5 | Round shrub, ash | Shrub maker | u | r | r | g | keep |  | r | g |  |  |
| 0x020002F4 | Wide shrub | Shrub maker | u | r | r | g | keep |  | g |  |  |  |
| 0x02001C36 | Shrub, End of Retail | Shrub maker | u | u | g |  | keep |  | r | g |  |  |
| 0x02001C34 | Tall shrub | Shrub maker | u | g |  |  | keep |  | g |  |  |  |
| 0x02001C31 | Shrub, dark | Shrub maker | u | u | g |  | keep |  | r | g |  |  |
| 0x020002F3 | Column shrub | Shrub maker | u | g |  |  | keep |  | r | g |  |  |
| 0x02000A59 | Tiny shrub | Shrub maker | r | g |  |  | keep |  |  |  |  |  |
| 0x020007BC | Gnarled stump | Gnarled tree maker | r | r | r | g | keep |  |  |  |  |  |
| 0x02000BAC | Dead bush | Gnarled tree maker | r | g |  |  | keep |  | g |  |  |  |
| 0x020004C7 | Burnt tree | Dead tree maker | r | g |  |  | keep | s | g |  |  |  |
| 0x02000AB6 | Black claw | Dead tree maker | r | g |  |  | keep | s | g |  |  |  |
| 0x0200071F | Leaning dead pine | Dead tree maker | r | g |  |  | keep | s | r | g |  |  |
| 0x02000847 | Large dead tree | Dead tree maker | r | g |  |  | keep | s | r | g |  |  |
| 0x020004B1 | Palm | Palm maker | u | r | g |  | back | s | r | g |  |  |
| 0x020007DA | Fan palm | Palm maker | u | g |  |  | keep | s | g |  |  |  |
| 0x02000214 | Broad palm | Palm maker | u | g |  |  | keep | s | g |  |  |  |
| 0x02000E71 | Jungle plant | Jungle plant maker | r | g |  |  | keep |  | g |  |  |  |
| 0x02000E72 | Jungle plant, wide | Jungle plant maker | r | g |  |  | keep |  | g |  |  |  |
| 0x020004B2 | Cycad | Cycad maker | g |  |  |  |  |  |  |  |  |  |
| 0x020004BC | Leaf stalk, yellow-green | Bladed plant maker | g |  |  |  |  |  |  |  |  |  |
| 0x020004BB | Leaf stalk, dark | Bladed plant maker | g |  |  |  |  |  |  |  |  |  |
| 0x02000583 | Reed | Reed maker | g |  |  |  |  |  |  |  |  |  |
| 0x02000A37 | Drooping flower, orange | Blossom maker | r | r | g |  | keep |  |  |  |  |  |
| 0x02000B2F | Drooping flower, red | Blossom maker | r | r | g |  | keep |  |  |  |  |  |
| 0x02000B2D | Drooping flower, magenta | Blossom maker | r | r | g |  | keep |  |  |  |  |  |
| 0x02000B2E | Drooping flower, purple | Blossom maker | r | r | g |  | keep |  |  |  |  |  |
| 0x020004C1 | Tall flower, magenta | Flower maker | g |  |  |  |  |  |  |  |  |  |
| 0x020004C2 | Tall flower, crimson | Flower maker | g |  |  |  |  |  |  |  |  |  |
| 0x02000CA4 | Pod, crimson | Pod maker | g |  |  |  |  |  |  |  |  |  |
| 0x02000CA6 | Pod, amber | Pod maker | g |  |  |  |  |  |  |  |  |  |
| 0x02000CA5 | Pod, green | Pod maker | g |  |  |  |  |  |  |  |  |  |
| 0x020010C8 | Bud stalk | Bud stalk maker | g |  |  |  |  |  |  |  |  |  |
| 0x020010CE | Bud stalk, short | Bud stalk maker | g |  |  |  |  |  |  |  |  |  |
| 0x020010C9 | Webbed plant | Webbed plant maker | g |  |  |  |  |  |  |  |  |  |
| 0x020010CF | Webbed plant, low | Webbed plant maker | g |  |  |  |  |  |  |  |  |  |
| 0x020010C6 | Twig tuft | Tuft maker | g |  |  |  |  |  |  |  |  |  |
| 0x020010CC | Twig tuft, red | Tuft maker | g |  |  |  |  |  |  |  |  |  |
| 0x020010C4 | Twig tuft, thin | Tuft maker | g |  |  |  |  |  |  |  |  |  |
| 0x020010D0 | Twig tufts, four | Tuft maker | g |  |  |  |  |  |  |  |  |  |
| 0x020010CB | Brown frond | Frond maker | g |  |  |  |  |  |  |  |  |  |
| 0x02000B3B | Green mushroom, broad | Mushroom maker | g |  |  |  |  |  |  |  |  |  |
| 0x02000B39 | Green mushroom, flat | Mushroom maker | g |  |  |  |  |  |  |  |  |  |
| 0x02000B38 | Green mushroom, tall | Mushroom maker | g |  |  |  |  |  |  |  |  |  |
| 0x02000B3A | Green mushroom, domed | Mushroom maker | g |  |  |  |  |  |  |  |  |  |
| 0x02000C68 | Pale mushroom, tall | Mushroom maker | g |  |  |  |  |  |  |  |  |  |
| 0x02000C69 | Pale mushroom, flat | Mushroom maker | g |  |  |  |  |  |  |  |  |  |
| 0x02000C6B | Pale mushroom, bell | Mushroom maker | g |  |  |  |  |  |  |  |  |  |
| 0x02000C6A | Pale mushroom, domed | Mushroom maker | g |  |  |  |  |  |  |  |  |  |
| 0x020014A8 | Sea fern, blue | Coral maker | r | g |  |  | keep |  |  |  |  |  |
| 0x020014A5 | Sea fern, red | Coral maker | r | g |  |  | keep |  |  |  |  |  |
| 0x020014A7 | Sea fern, green | Coral maker | r | g |  |  | keep |  |  |  |  |  |
| 0x020014AF | Sea star, red | Star plant maker | r | g |  |  | keep |  |  |  |  |  |
| 0x020014B0 | Sea star, green | Star plant maker | r | g |  |  | keep |  |  |  |  |  |
| 0x020014B2 | Anemone, green | Anemone maker | r | g |  |  | keep | s | r | g |  |  |
| 0x020014B4 | Anemone, blue | Anemone maker | r | g |  |  | keep | s | r | g |  |  |
| 0x02000247 | Cactus | cactus.py | g |  |  |  |  |  |  |  |  |  |
| 0x0200032C | Cactus, large | cactus.py | g |  |  |  |  |  |  |  |  |  |
| 0x0200032B | Cactus, round | cactus.py | g |  |  |  |  |  |  |  |  |  |

### The developer's notes (verbatim, short ids are the last four hex digits of 0x0200....)

Round 1:
- 322 Leafy oak: "These look like they are meant to be an Apple/Fruit Tree - rework with that in mind"
- 4BE Two-lobed ash: "Use the EoR as the baseline (all eras), and we need to give this an entirely different kind leaf"
- 4C7 Burnt tree: "Needs to be black and more branchy-twiggy, make it look EoR for all packs"
- 71F Leaning dead pine: "Entirely wrong color and is supposed to be a leaned over tree with moss on branches"
- 7BC Gnarled stump: "Wrong kind of plant - this is spuposed to be an almost alien-looking vine thing"
- 7D4 Great parasol tree: "Different kind of tree with broad leaves"
- 847 Large dead tree: "Entirely wrong color tree and needs moss on its branches"
- A37 Drooping flower, orange, B2D Drooping flower, magenta, B2E Drooping flower, purple, B2F Drooping flower, red: "Needs the weird alien-looking stamen to be represented more accurately - otherwise good"
- A59 Tiny shrub: "Wrong kind of plant - rework"
- AB6 Black claw: "Entirely wrong color"
- BAC Dead bush: "Needs to be more-brancy, twiggy"
- E71 Jungle plant, E72 Jungle plant, wide: "Needs fewer, larger leaves"
- 12FF Two-lobed ash, yellow: "Entirely new kind of leaf"
- 14A5 Sea fern, red, 14A7 Sea fern, green, 14A8 Sea fern, blue, 14AF Sea star, red, 14B0 Sea star, green: "Return to the original"
- 14B2 Anemone, green, 14B4 Anemone, blue: "Return to the original - but use the texture of the Pack version on the bulb body"

Round 2:
- 4B1 Palm: "Look at the trunk pattern - the former looks more like a pruned palm tree, we want that"
- A37 Drooping flower, orange, B2D Drooping flower, magenta, B2E Drooping flower, purple, B2F Drooping flower, red: "The original model may be a better bet - let's just rig it to blow in the wind"
- 12FB Spruce, snowy: "Needs a snowy base of trunk"

Round 3:
- 2F2 Round shrub: "Sparser leaves needed"
- 2F4 Wide shrub, 2F5 Round shrub, ash: "Too dark of leaves"
- 2F6 Spreading bush: "Probably a little sparser needed"
- 3EA Parasol tree, larger, 7D9 Bent parasol tree: "Flatter leaves, whiter trunk/stock"
- 7BC Gnarled stump: "I think this one should just stay with the EoR version, let's not do a custom tree"
- 12FC Crowned tree: "Good color, height needs adjustment, leaves should be drooping downward"

Keep picks (from tree-keep-picks.md; the 26 back and 39 keep are in the Pick column):
- 256, 258 pines: "Go back, but update leaf color to new"; 257: "Go back, but update leaf color - fix trunk transition"; 2D3: "Go back, but update leaf color"
- 322 Leafy oak: "Keep now, but make the leaves less dense, closer to how it was before"
- 3A2 Small pine, snowy: "Keep new but we need the leaves to have way more snow on them"
- AB6 Black claw: "Keep now, but we need to fix the trunk transition in the middle"
- 129A, 129B redwoods: "Keep now - but don't make the needles/leaves quite so dark"
- 14B2, 14B4 anemones: "Keep now, but we need the depth/relief map of the old one applied"
- 1C39 Spruce pair: "Keep now, but don't make the leaves quite so dark, bring the crown line up a bit."
- General: "be careful not to mess up trunk collision, be careful on trunk transitions"

Round 5 (chat, no saved verdicts): roots "starting too high and have the wrong shape", "certain tree types should never have these - like palm trees", then "I want to get rid of all root stuff" and "I want 0.4.45, but regenerated not to have giant bulbous trunks ... just without the trunk fitting logic". The client now collides with the drawn trunk instead (Pyreal feat/drawn-tree-collision).

Round 6:
- 240 Oak sapling, 246 Small oak, 251 Giant elm, 2D7 Elm, 2DC Elm, slender, 7D4 Great parasol tree: "Bring back the 0.4.4 version"
- 256 Middle pine, 257 Young pine, 258 Large pine, 2D3 Tall spruce, 2D8 Fir, teal, 2D9 Tall spruce, autumn, 2DA Giant spruce, autumn, 2DB Tall fir, teal, 322 Leafy oak, 3A3 Middle pine, snowy, 3A4 Large pine, snowy, 3A7 Tall spruce, snowy, 12FB Spruce, snowy: "Scale down to match original tree trunk diameter"
- 2F3 Column shrub, 1C36 Shrub, End of Retail: "Use the 0.4.4 version"
- 2F5 Round shrub, ash: "Lighten the leaves a bit"
- 3ED Banyan, low: "Scale down to match the height of the original tree. Fix the horizontal lines in the trunk root bends"
- 3EE Banyan, tall: "Scale down slightly to match the height of the original tree."
- 3EF Banyan: "Scale down slightly to match the height of the original tree. Fix the horizontal lines in the bends of the banyan tree trunk bends"
- 4B1 Palm: "Don't like the cross-hatched texture on the trunk, I want a texture much more similar to the retail"
- 71F Leaning dead pine, 847 Large dead tree: "Use the Retail model for this one, but use our updated bark textures and moss/leaf textures"
- 14B2 Anemone, green, 14B4 Anemone, blue: "Tone down the relief intensity on the bulb part by another 50%"
- 1C31 Shrub, dark: "Scale down to match the size of retail"

Round 7:
- 256, 257, 258, 2D3, 2D8, 2D9, 2DA, 2DB: "Match retail height"
- 3A3, 3A4, 3A7, 12FB: "Go back to 0.4.4 model and snowy leaves/needles, match retail height"
- 3EF Banyan: "Scale up to match retail height"

Banyan trunks (relayed in chat, 2026-11-23, not verbatim): jagged lines still showed in the offshoot trunks; slim the inner trunk so the offshoot trunks are close to its size. The developer picked 55% from three mockups, then asked for the stems to shrink too, so the whole trunk is about the size of retail's, and, after the retail overlay, to move it where retail's trunk stands.

Rounds 9 and 10 (via the screenshot session): "Keep the yellow twin as it is, but have 0x020004BE rolled back to 0.4.4. Also have 0x020002D9 rolled back to basically how it was in 0.4.4"; "The autumn trees in the cragstone shot, I think I also want those rolled back to the leaf colors they were in 0.4.4" (0x0200062B).

### State at 0.5

- On 0.4.4 models (grown by a copy of the 0.4.4 generator; gen_pack.mjs's KEPT list keeps them out of a full regrow, only `--only` grows them): 240, 246, 251, 2D7, 2DC, 2F3, 7D4, 1C36 (round 6); 3A3, 3A4, 3A7, 12FB with 0.4.4's snowy needles (round 7); 4BE one trunk with a full green crown and 2D9 with orange-brown needles (round 9). 62B has 0.4.4's orange leaves on today's shape (round 10).
- Every other tree is its 0.4.45 design with the developer's notes, grown as its generator grows it with no fitting to retail's collision; foot blended into the trunk (FLARE 0.3); conifers scaled to retail height from mesh measures; banyans scaled to retail height; 71F and 847 lean east on root plates as retail's do.
- Back on retail's own models (pack model removed): drooping flowers A37, B2D, B2E, B2F (sway entries, below); sea ferns and stars 14A5, 14A7, 14A8, 14AF, 14B0; gnarled stump 7BC (round 3: "stay with the EoR version"). Anemones 14B2, 14B4 are on retail's model with anemone.py pictures (0x05002C17, 0x05002C12) and half-depth bulb relief, halved again in round 6.
- The 0.5 manifest has 149 models: 93 `draws_on any` (the 90 plants, plus 0x0100069A, 0x02000285, 0x02000354: the hay pile and two ember beds), 13 older-era plants, 43 boulders.
- Removed tools: roots.py, blend_foot.py, fitFoot, fit_trunks.py `--to-head`, the redwood TREERING outlines. taper_trunks.py stayed out of the 26 regrown picks.

### Needle colour round (2026-11-21)

- Why: at a distance the 0.5 conifers read as solid near-black cones. Their needles were the yellow-green
  `Conifer_Needles.png` times a purple-leaning tint (`toned`), about 2% albedo, which no picture colour could
  bring to retail's hue (the picture has almost no blue).
- What: 256, 257, 258, 2D3, 2D8, 2DA, 2DB, 129A, 129B, 12FE and 1C39 draw their needles from
  `Conifer_Needles_Grey.png` (`grey_needles.py`: the picture's brightness, alpha kept, mean 0.1513 linear).
  Their tint (`crown` in gen_pack.mjs) is end of retail's crown colour, measured linear over its needles'
  area, over that mean, times `NEEDLE_GAIN` 2: at gain 1 Pyreal's lighting still drew them near-black
  beside retail.
- Left alone: 2D9 (0.4.4's autumn needles, round 9), the snowy 3A2, 3A3, 3A4, 3A7 and 12FB (0.4.4 needles,
  round 7), the older-era 3A1 and F06, and the sprig A59.
- Close up the needles read a little lighter and greener than retail's, and the teal firs bluer; the gain
  is the one knob.
- ee-pack draws each card from the level it takes over from (cards' make 2), as Pyreal's art-pack does
  since Pyreal 479b8aa5; the two packers write the same bytes in layouts 1 and 2.

### Kept deliberately

- Burnt tree 0x020004C7 at Yaraq is black on purpose: round 1 note "Needs to be black and more branchy-twiggy, make it look EoR for all packs", passed in round 2; confirmed again after the screenshot recapture. 0.4.0 drew it pale grey.
- Taller than retail was accepted in round 1 ("I don't need this changed"), later narrowed by the round 6 and 7 size notes for conifers, banyans, 322 and 1C31.
- Trees that lost wind (the 12 back on retail models and dead bush BAC) stay still, the developer's call. puffTree, wingTree and hayPile still use vertex colours the client doesn't draw; the developer passed them as they look.
- Spruce group 1C39, 1C31, 1C36 and 240 have no collision in retail; left without one.
- Small oak 246 and fruit tree 322 kept stout collision-fitted trunks at one point ("Keep collision fit"); superseded when all fitting was dropped.

### Older-era plant models (era-props review, drawn only on 1999 and 2005 records, `draws_on = "matching"`)

| Model | What | Commits | Checks |
|---|---|---|---|
| 0x02000253, 0x01000B74, 0x02000254, 0x01000B78, 0x020007A2, 0x020007A3, 0x020007A4 | fern, ferns, lilies, flower spikes EoR drew as other plants | bcbc66fd | round 1 "use our plant workflow"; built results looked right |
| 0x020002F1, 0x02000BAD, 0x02000BAE | young tree and red-brown twins as shrubs | 13fc194b, 1553379c, 018f49fe | round 2 sparser, lower; round 3 darker |
| 0x02000325 | giant tree as an elm | 13fc194b, 1553379c, 018f49fe | round 3 darker green like 2005's |
| 0x020003A1 | tall pine, EZ-Tree, dark teal | ce2b8338, 1553379c | needles near the ground |
| 0x02000F06 | fir, EZ-Tree | 1553379c, 018f49fe | needles dark green from a fifth of the way up |

The third check's fixes (018f49fe) were not shown again. Round 2 of era-props also passed a crystal 0x020003B6 as a plain keep and 0x020003B8 (lifestone book) as keep.

### Sway

`[[sway]]` for 0x02000A37, 0x02000B2F, 0x02000B2D, 0x02000B2E, wind 1 (51d3065d, Pyreal feat/retail-sway). Trees barely moved in game since Pyreal 49801dd8; Pyreal feat/tree-swing restores the swing.

### Looked at and left alone, or never reviewed

- Round 1 "Also in the pack" extras, offered and left empty: 43 boulders.py rock models, the six ground cover kinds, the hay pile and two ember beds. Boulder ids (43): 0x0100063D 0x01000A7B-0A7D 0x01000AB8 0x01000E0D 0x01001080 0x01001085 0x01001621 0x01001CCB 0x010036AD-36AE 0x01003A6B-3A6D 0x01004628 0x020003CB 0x020003E0 0x020003E2-03E3 0x020005C9-05D0 0x0200068C 0x020006C8 0x020006CC 0x020006CF 0x0200087C 0x020014A1-14A3 0x020014B5 0x020015D8-15D9 0x02001A22 0x02001A44-1A45 0x02001A9A
- Cacti 0x02000247, 0x0200032C, 0x0200032B (cactus.py): passed in round 1, never changed after.
- King's Crown water lily 0x020003D2 and round 4 prop plants (0x02000254, 0x010032CD, 0x020010CA, 0x0200009E, 0x01000DF0, 0x020004B0, 0x02001135, 0x020003F9) were sent "to the plants review" by the prop review; they are retail models with no pack model and were not reviewed there.
- Jungle tree atlas 0x05002601 and fern 0x050025F5: cut-out maps only (ground round 25, good).

### Branches (all inside archive/combined-before-squash-2026-11-21, content in 0.5)

era-props 018f49fe (older plants), era-props-trees e318f41e (rounds 1-4 and trunk fits), era-props-trees-sway 51d3065d, tree-picks c98a22b3 (picks, rounds 5-8), tree-rollback-044 15ec42da (round 9), tree-birch-044 703efe54 (round 10), trunk-taper d849fff5 (also in archive/pack-history-2026-11-21). Worktrees: dereth-enhanced-environment-wt/trees-review, tree-picks, era-props, flower-sway.

## 2. Armour and clothing

Scope: End of Retail pictures worn by characters, made by armor.py from `tables/armor.tsv` (one row per picture,
its suit, its parts). Every row in that table has been reviewed or is in the open round below. Review page
"Armour Review"; renders and lists in review notes armor-relief/
(textures.tsv for rounds 1-2, remaining.txt, clothing1-5/).

### Rounds

| Round (page round) | Date | Pictures | Cards | Verdict | Pack commit |
|---|---|---|---|---|---|
| Armour 1 (1): studded, chain, leather, plate | 11-19 made, 11-20 reviewed | 55 | 28 | 28 good, 0 bad | 5ef7f578 |
| Armour 2 (2): 20 sets, first pass | 11-20 | 216 | 140 | 140 good, 0 bad | 420a824a; rounds 1+2 squashed as 6b7ec972 |
| Armour 3 (3): last 18 sets with helms | 11-20 | 188 (185 + runic helms 0x050020D6-20D8) | 169 incl. 43 helm cards | 169 good | 3c6ea807 + 4d26ddbc, squashed 1cf20584 |
| Armour 4 (4): single pieces | 11-20 | 200 (111 items: 31 one-off helms, 80 coats, breastplates, leggings, gauntlets, boots, sleeves) | 216 | all good (the developer in chat, no page submit) | 22236daf |
| Clothing 1 (5): shirts and pants | 11-20 | 102 (51 bases) | 130 | all good (chat) | 522fdcc1 |
| Clothing 2 (6): robes, gowns, dresses | 11-20 | 260 (45 bases) | 214 | all good (chat) | e42df693 |
| Clothing 3 (7): masks, creature heads | 11-20 | 122 (64 bases) | 251 | all good except White Rabbit Mask 0x05002C26 ("too crinkled") | 2c9c8454 |
| Clothing 4 (8): hats, crowns, hoods | 11-20 | 57, plus the rabbit reworked as `hair` | 135 | hats all good; rabbit rework not marked | 16850eb9 |
| Clothing 5 (9): cloaks, slippers, apron, gloves, armbands, buckler cover | 11-20 | 33 (23 pieces) | 96 incl. rabbit | no verdict found in notes or transcripts | a6448419 |
| 0.5 | 11-21 | | | squashed into 1e0b6b0f | fbaee071 |

Before these rounds: Ethangar's Robe silk sheen was removed (silk.py and materials 0x0500E300-E308 gone, b0519de3, v0.3); its deep-cowl hood (the developer picked option 3, 2026-11-19) is a dat overlay, not the pack.

### Ids by round and suit

Suit names are `tables/armor.tsv`'s second column.

#### Armour round 1 (55)
- studded (13): 0x05000262 0x05000266 0x050002B5 0x050002DA 0x050002E2 0x050002E4-02E5 0x050002E7-02E8 0x050003D1 0x05000EC4 0x05000EC7 0x0500203E
- chain (12): 0x050000AA 0x050002B6 0x050002BB 0x050002C1 0x050002C8-02C9 0x050002CC 0x050002D1 0x050003CC 0x05000EC2-0EC3 0x0500203F
- leather (19): 0x050003CB 0x050003CE 0x0500222A-223A
- plate (11): 0x05000264-0265 0x050002B8 0x050002C6 0x050002CD 0x050002CF-02D0 0x050002D9 0x050002DF-02E0 0x0500203D
#### Armour round 2 (216)
- covenant (17): 0x050016D7 0x05001F9A-1FA9
- yoroi (10): 0x0500009C 0x050002BA 0x05000A8F-0A90 0x05000E65-0E6A
- scale (15): 0x05000263 0x05000267 0x050002B7 0x050002D2-02D5 0x050002D7-02D8 0x050002E1 0x050003CD 0x050003D0 0x05000EC6 0x05002040 0x0500315A
- helms (10): 0x0500019A 0x050003C8-03C9 0x05000EC8-0EC9 0x05001A45 0x05001A49 0x05001A4D 0x05001A91 0x05001A95
- diforsa (1): 0x05002AC4
- haebrean (10): 0x05002F28-2F30 0x05002F70
- alduressa (1): 0x05002AC3
- chiran (17): 0x05000CC0 0x05002396-23A5
- knorr (10): 0x05002F8C-2F95
- nariyid (11): 0x050023B4-23BE
- lorica (14): 0x050023A6-23B3
- koujia (8): 0x050001BA-01BD 0x050001C1-01C2 0x050001C7-01C8
- celdon (8): 0x0500009B 0x0500009D-009E 0x050000A7 0x0500018B 0x05000195 0x0500019B 0x0500019E
- amuli (7): 0x05001892-1898
- olthoi (37): 0x05002182 0x05002195-21A4 0x05002DD0 0x05002DD3 0x05002E18-2E29
- academy (6): 0x05001AF9-1AFE
- shadow (9): 0x0500301E-3026
- armoredillo (7): 0x050020EE 0x05002208-220A 0x0500220C-220E
- gromnie (15): 0x050002C7 0x05000EF8 0x050024B2 0x050024B4-24B6 0x050024B8-24BE 0x050024C0-24C1
- feet (3): 0x05002227-2229
#### Armour round 3 (188)
- olthoi-plain (19): 0x05001A44 0x05001A46-1A48 0x05001C46 0x0500217D-217E 0x05002181 0x05002185 0x0500218A-218B 0x05002DCE-2DCF 0x05002DD1-2DD2 0x05002DD5-2DD8
- o-yoroi (16): 0x050032A8-32AA 0x050032AD 0x050032B3-32B4 0x050032B8-32BD 0x050032C0-32C2 0x050032EB
- celestial-hand (15): 0x05002DE1 0x05002E3D-2E3F 0x05002E41-2E45 0x05002E47-2E4C
- eldrytch-web (15): 0x05002DE2 0x05002E58-2E65
- perfect-light (13): 0x05002DB8-2DBC 0x05002DD9-2DDB 0x05002DE4-2DE8
- noble (11): 0x0500257F-2589
- radiant-blood (13): 0x05002CBB 0x05002DE3 0x05002E4D-2E57
- fine-olthoi (9): 0x0500217C 0x0500217F-2180 0x05002183-2184 0x05002186-2189
- auroric-exarch (14): 0x050020CD-20DA
- leikotha (8): 0x05002B3B 0x05002B3D 0x05002B40 0x05002B42 0x05002B44-2B45 0x05002B47 0x05002B49
- ancient-armored (9): 0x05002388 0x0500242C 0x050024DB-24DD 0x050025A9-25AC
- gelidite (9): 0x05002B28 0x05002B3E-2B3F 0x05002B41 0x05002B43 0x05002B46 0x05002B48 0x05002B4A-2B4B
- prismatic-shadow (9): 0x050032FC-3304
- ancient-relic (7): 0x05002CA3 0x05002CA7-2CA9 0x05002CAC-2CAE
- exarch-plate (7): 0x05001B35-1B3B
- prismatic-celdon (7): 0x05002C4A-2C50
- thaumaturgic-plate (7): 0x05001B2E-1B34
#### Armour round 4, single pieces (200)
- sleeves-gloves (4): 0x050002C4 0x05001C09-1C0A 0x05002AD8
- jerkins (1): 0x050002CA
- leggings (15): 0x05000EFA 0x05002119-211A 0x0500211D 0x05002219-221B 0x05002220 0x050022AF-22B0 0x05002A8B-2A8E 0x05002ADA
- boots (17): 0x0500181E 0x05001979-197B 0x05001BCB-1BCC 0x050021D0-21D2 0x050022AA 0x05002A93-2A94 0x05002B29-2B2A 0x05002B4D 0x05002C3D-2C3E
- furs (9): 0x05001876 0x0500221C-221F 0x050022AB-22AE
- trench-coat (8): 0x05001878 0x0500187A-187B 0x0500187F-1880 0x0500188C 0x0500188F-1890
- helms-single (49): 0x05001A41-1A42 0x05001A4B-1A4C 0x05001A63 0x05001A93 0x05001B0D-1B13 0x05001BD0 0x05001BD3 0x05001BDB 0x05001C4C-1C4D 0x05001E8B-1E8D 0x05002202-2207 0x050022E6-22E7 0x05002309-230A 0x05002418-241B 0x05002ADB 0x05002B3C 0x05002B4C 0x05002BAC 0x05002BDE 0x05002C04 0x05002C8B 0x05002D13-2D16 0x05002D8E-2D90
- snake-skin (6): 0x05001BCD-1BCF 0x05001BD1-1BD2 0x05001BD4
- renegade (9): 0x05001C0C-1C0D 0x05001C0F-1C11 0x05001C1F 0x050023DF-23E1
- gauntlets (8): 0x05002041 0x05002143 0x05002AD3-2AD4 0x05002B53 0x05002C33 0x05002C6B 0x050032E1
- olthoi-fighter (1): 0x05002130
- hides (6): 0x050022B9-22BE
- ornate-tumerok (2): 0x05002413-2414
- ancient-armored (1): 0x0500242D
- wings (3): 0x050024B3 0x050024B7 0x050024BF
- gromnie-amuli (7): 0x050024C2-24C8
- girths (2): 0x050025AF-25B0
- tenassa (1): 0x05002AC5
- invader-lord-helms (8): 0x05002AE7-2AEE
- breastplates (7): 0x05002AF0 0x05002C23-2C25 0x05002CCE-2CD0
- coats (5): 0x05002B4E-2B52
- squalid (7): 0x05002BAD-2BB3
- prismatic-amuli (7): 0x05002C43-2C49
- relic-alduressa (1): 0x05002CA2
- ancient-relic (4): 0x05002CA4-2CA6 0x05002CAB
- noble-relic (12): 0x05002CAF-2CBA
#### Clothing round 1, shirts and pants (102)
- aerlinthe-shirts (5): 0x05001968-196C
- plain-shirts-pants (11): 0x050000A1 0x0500025D-025F 0x050002BD-02BE 0x050003CF 0x05000BB0 0x05000CBE 0x05000CEA 0x0500140D
- aphus (6): 0x050024A4-24A9
- battle-sparring (11): 0x050022EE-22F8
- tunics (4): 0x05002AAD-2AB0
- hide-shirts (9): 0x05002415-2417 0x05002BFC-2C01
- dapper-suit (7): 0x05002249-224F
- guardian-uniform (7): 0x05001E4C-1E52
- jaleh-chain (3): 0x05002118 0x0500211B-211C
- loincloth (1): 0x0500243C
- olthoi-fighter (3): 0x05002127-2128 0x0500212F
- poets-shirts (4): 0x05002A8F-2A92
- shou-jen (17): 0x05002CD1 0x05002CD4-2CD9 0x050032D3 0x050032D6-32DE
- shreth-hide (2): 0x05001AFF-1B00
- silken-wrap (8): 0x0500249B-249E 0x050024A0-24A3
- tusker-island (4): 0x05002082-2085
#### Clothing round 2, robes, gowns, dresses (260)
- aerfalle-pallium (3): 0x05001879 0x0500187C-187D
- ancient-armored-vestment (4): 0x0500233A-233D
- society-robes (30): 0x0500258A-2596 0x05002598-25A8
- asherons-raiment (8): 0x05002153-215A
- siraluun-dress (7): 0x05001A10 0x05001DE8-1DE9 0x05001DEB-1DEC 0x05001DF2-1DF3
- plain-robes (7): 0x0500187E 0x05001881-1885 0x05002ABF
- celestial-hand-robe (12): 0x050030BC-30BD 0x050030BF-30C8
- dho-robe (7): 0x0500310C-310D 0x05003110-3114
- doppelganger-robe (9): 0x050025E6-25EE
- eldrytch-web-robe (6): 0x050030C9-30CE
- elemental-master-robe (10): 0x05001FC0-1FC9
- elena-gown (6): 0x05002AB5-2AB6 0x05002AB8 0x05002ABA-2ABC
- empyrean-robe (3): 0x05002D3C-2D3E
- perfect-light-robe (16): 0x0500304C-305B
- envoys-robe (10): 0x050022FF-2308
- gelidite-robe (9): 0x050022DD-22E5
- reedshark-robe (10): 0x0500220F-2218
- kireth-gown (8): 0x05001A08-1A0F
- kiyafa-robe (11): 0x05001A11-1A18 0x05001A1B-1A1C 0x05001A20
- sasalia-dress (7): 0x05001A19-1A1A 0x05001A1D-1A1F 0x05001A21-1A22
- utter-darkness-robe (16): 0x05003280-328F
- luminous-robe (7): 0x05002BA4-2BAA
- martines-robe (8): 0x05001FF0-1FF7
- plaguefang-robe (8): 0x050022B1-22B8
- radiant-blood-robe (10): 0x050030CF-30D8
- realaidain-raiment (8): 0x050023BF-23C6
- shadows-garb (2): 0x05001A64 0x05001A66
- sleek-dress (9): 0x05002240-2248
- tessera-gown (6): 0x05002AB2-2AB4 0x05002AB7 0x05002AB9 0x05002ABE
- toga (3): 0x05002AC0-2AC2
#### Clothing round 3, masks (122)
- cloth-masks (24): 0x05001886 0x050019E8 0x050019EA-19EB 0x050019EE-19EF 0x05001AEF 0x05001DAB 0x05001E13 0x0500223C 0x0500264C 0x05002B73 0x05002C54-2C55 0x05002CDA 0x05002D11-2D12 0x05002DB3-2DB7 0x05002FAC 0x050032DF
- bone-masks (18): 0x05000E2B 0x05000E2D 0x05000E31-0E32 0x05001A3C 0x05001E14 0x05001E22 0x05001F66 0x0500202B 0x050021E5 0x050021E8 0x05002318 0x05002CE1-2CE2 0x05002F8A 0x05003306 0x0500330B 0x0500330D
- metal-masks (10): 0x05001AED-1AEE 0x05002136 0x050021DB 0x050021E6-21E7 0x05002D10 0x05002DFD 0x05002E03 0x05002E0A
- fur-masks (16): 0x050019C9-19CA 0x050019D0 0x05001A68 0x05001AE8 0x05001AEC 0x05001F61 0x050023CF 0x050023D3 0x0500257D 0x05002AC6 0x05002C26 0x05002DA6-2DA9
- hide-masks (54): 0x0500001B 0x0500001D 0x05000058 0x0500005B 0x05000C01 0x05000C04 0x05000C07 0x05001405 0x05001408 0x0500140B-140C 0x05001873 0x050018EF 0x050018F1-18F2 0x0500195B-195D 0x050019F4-19F5 0x050019F7 0x05001A33 0x05001A36 0x05001A67 0x05001AA7 0x05001AAB 0x05001AEB 0x05001DCD 0x05001E06 0x05001F5D 0x05002032 0x05002039 0x05002073 0x05002135 0x050021C8-21C9 0x05002312-2313 0x05002315 0x05002420 0x05002422-2423 0x050025AD 0x050025B6 0x05002C28 0x05002C96 0x05002CE3 0x05002DAA 0x05003305 0x05003307 0x0500330A 0x0500330C 0x0500330E 0x05003312
#### Clothing round 4, hats (58)
- fur-masks (1): 0x05002C26
- cloth-hats (25): 0x050002C3 0x050002E9 0x05001C35-1C36 0x05001C38-1C39 0x05001E3F 0x050020A0-20A1 0x05002148-2149 0x0500223D-223F 0x050022D6-22DA 0x05002AB1 0x05002EF0-2EF2 0x0500314E 0x05003152
- leather-hats (4): 0x05002146 0x050025BD-25BF
- fur-hats (7): 0x05001A65 0x05001C37 0x05002144-2145 0x050021FF-2201
- crowns (21): 0x05000E17 0x05000ECA 0x05001E18 0x05001E3E 0x05002027-2028 0x05002147 0x0500214A 0x050022F9-22FA 0x0500233E-233F 0x05002448-2449 0x05002B94 0x05002C18-2C19 0x05002C1B-2C1C 0x05002D0E 0x05003153
#### Clothing round 5, the rest (33)
- cloaks (15): 0x05002DF9 0x05003120-312B 0x0500312D 0x0500315F
- slippers (6): 0x05001E5C-1E5E 0x05002CDC-2CDE
- leftovers (12): 0x05000F59-0F5C 0x05001DF1 0x05001E0A 0x0500249F 0x05003094 0x050032BE-32BF 0x050032E0 0x050032E2

### Looked at and left alone

- Faces and open-helm face pictures (over 60% skin entries) are face-detail's area, not armor.py: head pictures 0x0500024C, 0x050002F5, 0x0500025C, 0x05000098-009A; O-Yoroi and open-helm faces 0x05003101-3104, 0x0500315B, 0x05003164-3165; O-Yoroi, Eldrytch Web, Radiant Blood and Noble Relic helm faces; Lyceum Hood face 0x050030EF; Elysa's face 0x0500103F.
- 0x050025BC (Viamontian Lord's Helm, the spiked plate stand) is arms.py's; armor.py skips any picture another tool covers.
- Maps-only cards (not worn on the review figure): buckler cover (shield slot 21), Rynthid Ravager 0x05003306 (Lugian and Tumerok bodies), Silken Wrap band (Lugian only), 0x0500249F, 0x050032BF, 0x050032E2.
- Not done at all: 1999 and 2005 armour and clothing (End of Retail only), shields beyond the buckler cover, creatures.
- Golems (golems.py, 0x050018B7-18D1, 0x0500190C, 0x05001310, 0x05002C05-2C06) and cobwebs were made in 0.1 and never put through a review round.

### Branches

- fix/armor-relief a6448419: all rounds; in archive/combined-before-squash-2026-11-21. Worktree dereth-enhanced-environment-wt/armor.
- armor-relief-presquash 420a824a: unsquashed rounds 1-2 (5ef7f578, 420a824a) on an older room-relief base. Its armor.py and armor.tsv are identical to 6b7ec972 and none of its material differences are armour ids. Nothing to recover.
- armor-r3-presquash 4d26ddbc: unsquashed round 3 (3c6ea807, 4d26ddbc). Tree identical to 1cf20584. Nothing to recover.

## 3. Props and items

### Before the prop texture review

| Asset | Work | Date, commit | Verdict |
|---|---|---|---|
| Iron doors 0x020005DA (also 0x020005F1, 0x0200024F) at 0x7F03: 0x05001777, 0x05002635, 0x05000EE2 iron; 0x05002620, 0x05002638, 0x05000D25 banded wood | iron.py metal and metal maps, roughness 0.3 then 0.4 | 11-17, 3d26751f, 9cad3f77; v0.3 | softer sheen shipped |
| Training Academy books: 0x05000B15 bookcase front, 0x05000AD1 open page, 0x05000DFB page edges | books and pages recipes | 11-17, 5b75e0d0; v0.3 | The developer chose medium depth and satin gloss. Left alone then: covers 0x05000ACE, spine 0x05000ACD, painting 0x05002685 (0x05000ACE later changed in prop round 4) |
| Arms at 0x7F03: 0x050025BC, 0x050002A2, 0x05000C53, 0x05000C54, 0x05000C55, 0x05000FDD, 0x0500029E, 0x05001D9C, 0x05001D9D, 0x05001E0E (models 0x010002EB, 0x01000305, 0x02000ADD, 0x02001255) | arms.py metal | 11-17, 5979d0d7; v0.3 | shipped. Follow-up candidates never done: 0x05000A8A, 0x05000E18, 0x05000C56 |
| Iron chest 0x05000A6E lock plate, 0x05000A6F sides, 0x05000A70 lid (setups 0x0200007C, 0x02000A23, 0x02001250), every era | iron.py plates (1c542739), then chest.py paints new pictures at 4x texels (ba8c3feb) | 11-20 | era-props round 2 asked for it ("materials task"); new pictures merged |
| Stone head 0x020003B1 and boulder 0x020003B2: 0x05002755-2759, 0x05001E76; 2005 0x05001E79, 0x05001E7B, 0x05001E7C, 0x05001E7D | carved recipe at 512 | 11-20, 1c542739 | era-props round 2: "don't re-tint" (they never were) |
| Bael'Zharon statues: solid surfaces 0x080006F7 and 2005 0x08000203 (setups 0x02000359, 0x020007C3, 0x02000A53, 0x02000A54) | solids.py `[[solid]]` chiselled stone | 11-20, e93132f2 | The developer: "Chiselled stone, make all versions use the EoR version" |
| Torch pillars 0x0200039C, 0x0200039D | `[[light]]` in front of the flame | 11-20, 1553379c, 1ac414de | era-props round 2 redo, then fixed |
| Golems, obsidian ground, mud, silk cobwebs, stones, cut-out foliage, quantised models | first generators | 11-14, efdcb967, 90b6ffc3 (0.1, 0.2) | no review round |
| Crystal creatures: the shards' picture 0x05000E18 in their template palettes 0x04000BEE, 0x04000BF0-0BF7, 0x04000FDC-0FDE, 0x0400151D-1521 (setups 0x02000700-0713, 0x020008F9-08FC, 0x02001AC7: Crystal Shard Sentinel, Crystal of the Dark Isle, Fire, Acid, Fenmalain, Rynthid Crystal, Crystal Moiety and the rest), and the cistern pillars' 0x05001F99 (0x020010A2), each with its 2005 picture | crystals.py clear 0.65, refraction 1.75; the black shards (0x04000BF7, 0x04001521) clear 0.25; pillars clear 0.65, refraction 2.0. relief.py's 0x05000E18 material names the picture's own palette 0x04000BEF, so the world's crystal clusters keep it; the blue shards (template 2, the same palette) name it in `laid_palettes`, drawn clear by a Pyreal that tells a look's palette from a picture's own (review/crystal-creatures) and retail by an older one. Bloodstones 0x05002FAD left alone: clear lost their red glow. Crystal Lord, Sovereign and Minion already draw the gem golems' 0x050018C9/0x0500190C | 11-23, 75f6ec2d, 7dfef30e (crystal-creatures) | not yet shown to the developer |

### Prop texture review (most placed End of Retail props first)

Survey and pages: `pyreal/notes/review/prop-textures/` (props.tsv 3,666 placed props, pictures.tsv 2,193 pictures,
page/r1-r4.json, round4*.json). One review page per round. Fault found: every height map spanned its full range
whatever the prop's size; fixes keep relief to millimetres (`mm=`) and raise iron on wood (`:iron=`).

| Round | Date | Cards | Verdict | Commit |
|---|---|---|---|---|
| 1 | 11-21 | 9 | all 9 fix approved | ade4a258 |
| 2 | 11-21 | 9 | fix 2, keep 7 | 8b9c7c2f |
| 3 | 11-21 | 10 | fix 6, keep 4 | 21ab639e |
| 4 | 11-21 | 50 | fix 28, keep 21, rework 1 (stone bench, done) | 86ea9006 |
| 0.5 | 11-21 | | squashed into 547c3224 | fbaee071 |
| 5 | 11-22 | 50 | fix 20, keep 24, rework 6 (all six fixed in reworks 1 and 2) | ea0d87cf, 1e0628a5, e35d8e1a |
| 6 | 11-22 | 59 | fix 17, keep 31, rework 11 (10 fixed in the rework: glass, glaze, canvas, water, crystal, iron; Thorsten Cragstone's Armor was already metal) | a9d71af0, 8b1b0bc2 |
| 7 | 11-22 | 35, then 10 rechecked | 35 fix (crystals, gems, pottery, bottles); recheck fix 6, keep 4 | b9b7984b, 27668703 |
| 8 | 11-22 | 4 crystal, 16 metal, 9 chests | crystals polished, Life Stones clear 0.55; metal fix 16; chests fix 8, rework 1 (done) | 6d80881a, de78a609, 1ee4ee03, 1e261583, 38edef2d, 458b4926 |
| 9 | 11-22 | 51 | fix 21, keep 28, rework 2 (both fixed) | ccc414ac, bbd1e705, 862bed2f, c2f8acdb |
| 10 | 11-24 | 6 clear maps, then 2 | clear maps fix 5, rework 1 (the champagne, painted anew as Dom Pyrignon and passed) | 167ec97c, 5e9b7b82, 36a272bb, cb0d2cab |
| after 10 | 11-24 | | the crystal picture 0x05000E18 clear; both hay piles straw heaps, the large one at retail's height | 1fc96a2a, fe4d22ed, d56c42df |
| 0.5.4 | 11-24 | | rounds 5-10 and the work after them released | ef5acc26 |
| 11 | 11-25 | 28 (props.tsv ranks 627-824), then 7 | fix 14, keep 8, rework 6 (all six fixed in the rework, and the dark statues made metal) | fff7dfaf, f7ec5465 |
| obelisk | 11-25 | 2 options | option A fixed with the clear lowered and the bend raised; option B not taken | 42cec6fd |
| 12 | 11-25 | 28 (props.tsv ranks 828-943) | fix 14, keep 12, rework 2 (both fixed: the lava floor, and the cabinet shaped by hand) | 25607fa3 |
| bookshelves | 11-25 | 4 | all four fixed on the third page | 4d8b8c00 |

Round 1, all fixed:
- Wall torch 0x020001E5, 0x020001EB, 0x0200026D: 0x050010C4 plate, 0x05002A9F handle
- Dungeon chair 0x02000121 and crates 0x02000267, 0x02000266, 0x0200011E, 0x0200016D: 0x05000C92 back and crate side, 0x05000E13 seat
- Cask 0x020000A5: 0x05000A91
- Standing torch 0x020005D9, 0x020005D8: 0x05000AF7 head, 0x0500141A stand
- Hanging chain 0x01000E0E: 0x05001417
- Bench 0x02000120: 0x05000E13
- House door 0x020019FF: 0x05002F96
- Numbered dungeon signs 0x010028F9, 0x010028F7, 0x010028F6 and series: 0x05001EC7-1ECF
- 2005 pictures that borrow these recipes (0x05000408, 0x05000A91, 0x050010C4, 0x0500141A) were not remade.

Round 2:
- Fixed: lantern 0x020001BD and 11 more (0x05000B2B, 0x05000B2C, 0x05000B2D drawn flat); barred dungeon door 0x02000281 and 0x01000A29 (0x05002677 wood mm=3). 2005 0x05000B2B, 0x05000DB9 remade.
- Kept: dungeon post 0x010000DE (0x05002620); dungeon door 0x0200024F (0x05000D25, 0x05002620); stone marker 0x0200104E (0x05002350, 0x05002356, 0x0500235E); plank platform 0x01000E2A (0x0500267C); stone spire 0x02000248 (0x050027A3); timber archway 0x020001E7 (0x05002638, 0x05002620); wooden stairs 0x02000A4A (0x05000E5C, 0x05001029, 0x0500267C).

Round 3:
- Fixed: defense battery and traps 0x020000EB (0x0500027A mm=3, 0x0500040A flat); orange mushroom 0x02000175 and 9 more (0x05000AF2 mm=4, 0x05000AF6 flat); iron chandelier 0x02000081 (chain 0x05000B18 iron mm=3); blue mushroom 0x02001138, 0x0200113E and 6 more (0x050024CA mm=3); log pile 0x0200010A (0x05002B91 rock mm=6); stone font 0x02000242 (0x05000D31 mm=4). 2005 0x05000B18 and 0x05000D31 remade (2005 chain not metal).
- Kept: rock columns 0x02000D68, 0x02000D67 (0x0500123D); rail fence 0x020003B5 (0x0500268B); wooden spire 0x01001126 (0x050026CC, also 25,000 floor uses); slime corner 0x0200028D (0x05000EEA).
- Left: the chandelier ring is the iron chest's 0x05000A70 (chest thread).

Round 4 rule: relief deeper than about a tenth of a picture's size keeps its recipe at mm = 1.5 + a tenth of its smaller side in cm (2 to 12); 16 texels or smaller is drawn flat (0x050017B0 lost its material). 41 new rows, 7 hand rows gained mm, 17 2005 borrowers remade.

Round 4 fix cards (model: pictures changed):
- Bed 0x0200016D/0x02000270: 0x05000BE4
- Carved pillar, red chevrons 0x02001055: 0x05002360 0x05002363 0x05002364 0x05002365
- Earth mound 0x02000586/0x02000584/0x02000AB4: 0x05000EE9
- Low table with a rug top 0x02000368/0x02000369: 0x050010EA
- Stone stand 0x020005B6/0x02000626/0x0200034C +2: 0x05000DAF
- Street lamp 0x0200071A: 0x05000B43 0x05000BA7
- Carved stone tablet 0x0200111D: 0x050010F8
- Stone altar block 0x02001051: 0x05002354 0x05002355
- Stone bench 0x02000971/0x0200093B: 0x050019F9 0x050019FA  (rework: 0x050019F8 top mm=1)
- Floor mat with writing 0x01000A6A: 0x05000DEE
- Stone column with a stair 0x010000EE: 0x0500271B
- Forked staff 0x020009A3: 0x0500179F 0x050017B0 0x050017BA
- Tall torch 0x02000AB9: 0x05002641
- Egg 0x02000AE1: 0x0500167F 0x05001680
- Hooded statue, green 0x020011AA: 0x050024FC 0x050024FF 0x05002501
- Hooded figure on a rock 0x0200039C: 0x0500120F
- Open book (Rheaga's Journal) 0x02000154: 0x05000ACE
- Floating shards 0x0200105A: 0x0500234F 0x05002351 0x05002352 0x05002366
- Woven basket 0x0200035B: 0x05000ACC
- Mushroom cluster 0x02001139: 0x050024CC
- Button 0x0200011A: 0x05000B09
- Lantern staff 0x02000451: 0x05001377
- Gilded altar box 0x0200096A: 0x05001A3D
- Riveted stone stool 0x02000624: 0x05002683
- Fountain 0x0200027B: 0x05000E1C
- Kelderam's Tomb 0x020009AC: 0x050010F7
- Hammer 0x010007A8: 0x05000B0B 0x05000C54
- Bookcase 0x02001205: 0x050026E2
- Legendary Armor Chest 0x02000F34: 0x05001C08 0x05002114 0x05002115 0x05002116 0x05002117

Round 4 keep cards (model: pictures, unchanged):
- Clay jug 0x0200035E/0x0200036E: 0x05000A8C; Rock corner 0x02000AB3: 0x05001D70; Small stone piece 0x02000294: 0x05000E98; Dark arch door 0x020005F2: 0x05002628 0x050027EF; Carved wooden pillar 0x02000D73/0x020003C7/0x02000D72 +1: 0x05002696; Hanging hide 0x02000186: 0x05000B58; Rug 0x01000170: 0x0500268C; Mossy stone block 0x020011F8: 0x05002703 0x05002706; Stone stairs 0x010000D1: 0x05002682; Stone couch 0x02000122/0x02000187/0x020006F7: 0x05000E1F; Earth ramp 0x0200068B/0x020006C9: 0x0500122C; Dark crystal spike 0x02000F36: 0x05001C8E 0x05001C92; Dark rock corner 0x02000205: 0x050026AE; Black stone urn 0x02000452: 0x0500279E; Vase 0x02000293: 0x05000E95; Red timber frame 0x02000CA3: 0x050027ED; Painted screen 0x01000A69: 0x05002690 0x05002691; Wooden gable 0x010000D6: 0x050026B0; Sack 0x02000606: 0x050017A9; Dark spike 0x01002A03: 0x050018A1; Sliding door 0x02000310: 0x05002A87


### Prop texture rounds 5-12 (2026-11-22 to 2026-11-25)

Pages: "Prop Texture Review, Round 5" to "Prop Texture Review, Dom Pyrignon" (claude.ai artifacts); card data in
`pyreal/notes/review/prop-textures/page/r5.json` to `r10c.json`. From round 7 every card also says what the prop is
made of, and the fix gives it that material (glaze, glass, crystal, metal, canvas, water), not only relief. Dates are
the dates the verdicts were sent. Models and pictures as in round 4: model, then its pictures.

Outcomes worked out in conversation rather than on a card:
- Round 5: the Life Stone 0x020002EE was left unchanged at first ("Don't change the Lifestone at all"); round 8 later
  made its crystal clear.
- Round 8: both Life Stone cards came back marked fix; the developer chose clear. Glacier ice (de78a609) was "too
  overdone", so the crystals 0x05002B92 and 0x05001773 became clear 0.55, refraction 1.55 (1ee4ee03). The blue
  crystal of the Obsidian Plain and the Crystal Shards were polished (6d80881a).
- Round 8: Jaleh's Finery Chest 0x02000F30 (and the Armor and Magic Chests) lost its relief and keeps only its steel
  and gold (458b4926).
- Round 9: the dark stone column 0x0200085E takes the relief of its coloured twin 0x0500275F (862bed2f), and its
  middle bands 0x0500275C, 0x0500275E the same stone relief (c2f8acdb).
- Round 10: the wine bottle report (cork drawn as glass) led to clear maps: a clear material's map marks what is
  clear (red) and what of the rest is metal (green), with Pyreal reading it (feat/clear-map, Pyreal main). The
  champagne 0x020012B6 was first traced, then, as End of Retail holds its pictures in 32 dark colours and the 2005
  painting may not be copied, painted anew by champagne.py as "Dom Pyrignon, Vintage P.Y. 10" (Pinyon Script, SIL Open
  Font License). One material matches both eras' pictures, so the 2005 world draws it too.
- After round 10: the shared crystal picture 0x05000E18 (palette 0x04000BEF) is clear 0.55, refraction 1.55 in every
  world, so the 1999 and 2005 Life Stone match End of Retail's; the world crystal clusters share it and turned clear
  too. Both hay piles are shapes.mjs `haystack` heaps (0x0100069A small, 0x0200040F large at retail's 2.5 m, since
  the game still walks on retail's mound).

#### Round 5 (11-22)
Fixed:
- Octagonal grate 0x0200046A: 0x05000EE2 0x05000EE3 0x0500121B 0x05001777 0x05002635 0x0500265F
- Pale egg 0x01003450: 0x050024CF 0x050027DB
- Wooden cart and wall hanging 0x01000E5F: 0x050010C3 0x050010C5 0x050010C6 0x050010C7 0x050010C8 0x0500263D 0x0500268E 0x0500268F 0x0500272A
- Weapon rack 0x02001287: 0x050026D0 0x050026D1. Note: "Do we have proper materials for this?"
- Number sign 0x010028F4: 0x05001ED0
- Crystal lamp post 0x02000719: 0x05000CCA 0x05001401 0x05001891
- Wooden post 0x0200020E: 0x050026C3 0x0500289F
- Painted pot 0x02000948: 0x050019FC 0x050019FD
- Lever 0x0200031F: 0x05000C52
- Corpse 0x0200037B: 0x05000BFE 0x05000BFF 0x05000C00 0x05000C01 0x05000C02 0x05000C03 0x05000C04 0x05000C05 0x05000C06 0x05000C07 0x05000C08 0x05000C09 0x05000C0A
- Thorn staff 0x02001136: 0x05002400
- Antique Platter 0x020001F2: 0x050002AB
- Bronze Candlestick 0x02000106: 0x050003D2
- Wall shelf 0x01000ACC: 0x05002850 0x05002851
- Urn with scattered tools 0x02001050: 0x05000E27 0x05000E28 0x05000E2C 0x05000E35 0x05002359 0x0500235C
- Broken wheels 0x02000BBD: 0x050018BD 0x050018BE 0x050018C1 0x050018C2 0x050018C3 0x050018C4
- Carrot 0x020006FC: 0x05000ADD 0x05001871
- Roast bird 0x02000177: 0x05000AE3
- Candelabra 0x02000105: 0x05000293
- Rolled scroll 0x02000182: 0x05000E20
Sent back:
- Mossy carved block 0x020011FB: 0x050027CD 0x050027CE. Note: "Something very wrong with relief map on this wall texture"
- Dark floor mat 0x01004298: 0x05002EAB. Note: "If this is a floor mat and not a dungeon tile, the relief is too high"
- Emblem rug 0x01000EBB: 0x050010EE. Note: "The depth mapping should almost be inverse, the patterns on the pillow would be raised from the surrounding area, not lowered"
- Life Stone 0x020002EE: 0x05002B93. Note: "Don't change the Lifestone at all."
- Well 0x02000180: 0x05000BCE. Note: "Brick could use some extra relief maybe?"
- Lifestones sign 0x0200062E: 0x050017FA 0x050017FB 0x05001804. Note: "Text on parchment should be raised above surface. Parchment should be raised above brick/stone behind it. Brick/stone can have some moderate texture, and border of brick should be even lower."
- Kept: Dark sloped awning 0x010009D3: 0x05002929 0x0500292A; Dark rock lump 0x010009C7: 0x05002661; Jewelled rock 0x02000AC9: 0x05001D83; Purple swirled rock 0x02000F42: 0x05001DFD; Guardian door 0x02001056: 0x05002707; Red jewelled rock 0x02000AC7: 0x05001D85; Red crystal obelisk 0x02000BBF: 0x05001E5F 0x05001E62 0x05001E63; Blue crystal 0x020007E1: 0x05002721; Flat mushroom 0x02000AC1: 0x05001D89 0x05001D8A; Dark folded panel 0x0200067F: 0x050026AD; Wooden stairs 0x020003C4: 0x05002695; Campfire 0x020005AE: 0x0500260C; Pale rock slab 0x020004BF: 0x05000FF3; Dark framed painting 0x0200018F: 0x05002684; Mossy column 0x01004191: 0x05002E13; Carved chair 0x02001267: 0x05002801; Brick arch post 0x02000384: 0x0500281D 0x0500281E 0x0500281F 0x05002820; Green spotted crystal 0x020017E8: 0x05002DF6; Pale chair 0x01003585: 0x05002519; Bed 0x0200097F: 0x05001A69; Court painting 0x02000190: 0x0500267E; Grey framed painting 0x0200018E: 0x05002679; Brick stair block 0x01000A2F: 0x05002678 0x050026F1 0x0500280A; Dark horn 0x01004D3A: 0x05003310.

#### Round 5 Rework (11-22)
Fixed:
- Dark floor mat 0x01004298: 0x05002EAB
- Emblem rug 0x01000EBB: 0x050010EE
- Life Stone 0x020002EE: 0x05002B93
- Lifestones sign 0x0200062E: 0x050017FB 0x050017FA 0x05001804
- Weapon rack 0x02001287: 0x050026D1 0x050026D0
Sent back:
- Mossy carved block 0x020011FB: 0x050027CD 0x050027CE. Note: "There's still a very strange distortion coming from somewhere in the center - right under the top border"
- Well 0x02000180: 0x05000BCE. Note: "This brick texture isn't rectangular bricks, it is stone we need to trace around - we have other ways of dealing with more natural stone shapes"

#### Round 5 Rework 2 (11-22)
Fixed:
- Mossy carved block 0x020011FB: 0x050027CD 0x050027CE
- Well 0x02000180: 0x05000BCE

#### Round 6 (11-22)
Fixed:
- Beer Keg 0x02000975: 0x050002A2 0x05000B31 0x05000C53 0x05000C55
- Log 0x02000277: 0x05000E12
- Striped hide 0x020006D2: 0x05000127 0x050002C4
- Framed map 0x01002510: 0x05001D2B 0x05001D2C 0x050023DB 0x050026BF
- Dark arch 0x0200004F: 0x05000378 0x05002789
- Painted tapestry 0x02000961: 0x05001A02 0x05001A03 0x05001A04 0x05001A05 0x05001A07
- Gargoyle statue 0x0200042B: 0x0500120C
- Noble Swordstaff Chest 0x02001149: 0x050024D0 0x050024D1 0x050024D2 0x050024D3
- Dark jug 0x020000EA: 0x05000BE6
- Painted urn 0x02000EE7: 0x05000E9A
- Large book 0x01004959: 0x0500215C 0x0500318D
- Large Golden Coin 0x02000172: 0x05000AF9
- Anvil 0x020011BF: 0x05002516 0x05002517 0x0500270D
- Town name signs 0x01002944: 0x05001EBC 0x05001EBD 0x05001EBE 0x05001EBF 0x05001EC0 0x05001EC1 0x05001EC2 0x05001EC4 0x05001EC5 0x05001EC6
- Hanging lantern 0x0200032E: 0x05001422
- Renegade Chest 0x020010A4: 0x050019D2 0x050019D4 0x050019D5 0x050019D6 0x050019D7
- Number card 9 0x010028F4: 0x05001ED0
Sent back:
- Pool with a little tree 0x02000227: 0x050001EE 0x05000280 0x05000ADF 0x05000AE0 0x05000AE1 0x05000AE2 0x05000AE7 0x05000AE8 0x05000AF3 0x05000AF4 0x05000B19 0x05000B30 0x05000FA3 0x050017B2 0x050017B3. Note: "Make the water in this reflective water"
- Green bottle 0x02001288: 0x050026DA 0x050026DB 0x050026DC. Note: "Make this a translucent glass material"
- Leather satchel 0x02000150: 0x05000281 0x05000282 0x05000283. Note: "Make this a fabric/canvas material"
- Cooking pot 0x02000604: 0x050017B5. Note: "Make this a shiny ceramic material"
- Thorsten Cragstone's Armor 0x02000ADD: 0x05001D9C 0x05001D9D 0x05001E0E. Note: "Ensure this is metal material if it isn't already"
- Patterned jug 0x0200100A: 0x05000E97. Note: "Make this a shiny ceramic material"
- Green jar 0x02000602: 0x050017A1. Note: "Make this a shiny ceramic material with wood/metal top"
- Blue jar 0x020000A6: 0x05000FA0. Note: "Make this a shiny ceramic material with wood top"
- Iron-framed double door 0x020010A8: 0x05001FEB. Note: "Make sure this is getting appropriate metal and wood materials in right places"
- White crystals 0x01001BC9: 0x05001912 0x05001913 0x05001914. Note: "Give these a crystal material"
- Mossy brick pillar 0x02000415: 0x05002693 0x050027A4. Note: "These grout lines are inverse and sticking out above the bricks"
- Kept: Wall lever 0x02000261: 0x05000A6B 0x05000B08 0x05000B33; Dark wedge 0x02000206: 0x05002663; Long table 0x0200094D: 0x05001A00; Low bookshelf 0x02000BAF: 0x05000B15; Blue pool floor panel 0x02000DBD: 0x05002017; Low wooden crate 0x01000E70: 0x0500295C; Stone pyramid 0x02000989: 0x050026AA; Purple glow floor panel 0x02000DC3: 0x05002014; Green glow floor panel 0x02000DC1: 0x05002016; Clay oven 0x0200033C: 0x05002793; Red banner 0x02001259: 0x050026CE; Stone stair 0x02000621: 0x050026CA; Stone counter 0x01003605: 0x050028DF 0x0500291F; Scholar painting 0x02000191: 0x05002685; Wooden raft 0x02000222: 0x050017F0; Stone column 0x01004192: 0x05002E11 0x05002E14; Stone face 0x01003480: 0x05002361; Spotted shell 0x010033D5: 0x0500196D; Orange glow floor panel 0x02000DBF: 0x05002015; Octagonal floor platform 0x01003F71: 0x050018A0 0x050027AA 0x0500291E; Locked Door 0x0200167D: 0x05001ACA 0x05002A9E; Urn with scattered tools 0x020011C0: 0x050027FA; Tree stump 0x02000E7D: 0x0500209A 0x0500209B; Number card 0 0x010028F6: 0x05001EC7; Number card 2 0x010028F7: 0x05001EC9; Number card 3 0x010028F0: 0x05001ECA; Number card 4 0x010028F2: 0x05001ECB; Number card 5 0x010028F5: 0x05001ECC; Number card 6 0x010028F1: 0x05001ECD; Number card 7 0x010028F8: 0x05001ECE; Number card 8 0x010028F3: 0x05001ECF.

#### Round 6 Rework (11-22)
Fixed:
- Pool with a little tree 0x02000227: 0x05000FA3
- Green bottle 0x02001288: 0x050026DB
- Leather satchel 0x02000150: 0x05000281 0x05000282 0x05000283
- Cooking pot 0x02000604: 0x0500179F 0x050017B5
- Patterned jug 0x0200100A: 0x05000E97
- Green jar 0x02000602: 0x050017A0 0x050017A1
- Blue jar 0x020000A6: 0x05000FA0
- Iron-framed double door 0x020010A8: 0x050021FB 0x05002018 0x05001FEB
- White crystals 0x01001BC9: 0x05001912 0x05001913 0x05001914
- Mossy brick pillar 0x02000415: 0x05002693

#### Round 7 (11-22)
Fixed:
- Beer stein 0x02000976
- Blue decanter 0x020000A9
- Glazed pot 0x02000A0F
- Ale bottle 0x02001257
- Crucible 0x020005FE
- Dye vial 0x0200090F
- Angree's Angry Ale 0x02001256
- Tusker Spit Ale 0x02001258
- Bottle of Crystal Champagne 0x020012B6
- Stolen Ewer 0x02000173
- Urn 0x02000293
- Vase 0x02000294
- Potion flask 0x020000AB
- Oil vial 0x020005FD
- Chalice 0x020000E5
- Pearl 0x02000EF3
- Strange Crystal 0x02001A86
- Hardened Shard 0x02000EB9
- Aquamarine Prisms 0x0200111C
- Amethyst Cradle 0x0200111A
- Jade Dais 0x02001119
- Adjanite Gem 0x02001118
- Attunement Crystal 0x02000FA7
- Scored Shard 0x02000EB6
- Brilliant Shard 0x02000EB7
- Solid Shard 0x02000EBC
- Plated Shard 0x02000EBB
- Seared Shard 0x02000EB8
- Chilled Shard 0x02000EB2
- Charged Shard 0x02000EBA
- Crystals of Grace 0x02000DD3
- Eye of the Depths 0x02001116
- Beholding Adjanite Gem 0x0200111B
- Decorated Adjanite Gem 0x02001117
- Entrancing Adjanite Gem 0x02001113

#### Round 7, Signed Off Before (11-22)
Fixed:
- Clay jug 0x0200035E
- Painted urn 0x02000EE7
- Painted pot 0x02000948
- Urn with scattered tools 0x02001050
- Urn with scattered tools (second) 0x020011C0
- Crystal lamp post 0x02000719
- Kept: Red crystal obelisk 0x02000BBF; Green spotted crystal 0x020017E8; Jewelled rock 0x02000AC9; Red jewelled rock 0x02000AC7.

#### Round 8 (11-22)
Fixed:
- Blue crystal, polished: 0x05000E18
- Life Stones, polished: 0x05002B92 0x05001773 0x050020B0
- Life Stones, clear: 0x05002B92 0x05001773 0x050020B0
Unmarked:
- Blue crystal, clear: 0x05000E18

#### Round 8 Metal Recheck (11-22)
Fixed:
- Street lamp 0x0200071A
- Riveted stool 0x02000624
- Legendary Armor Chest 0x02000F34
- Octagonal grate 0x0200046A
- Crystal lamp post 0x02000719
- Lever 0x0200031F
- Wall lever 0x02000261
- Bronze Candlestick 0x02000106
- Candelabra 0x02000105
- Beer Keg 0x02000975
- Noble Swordstaff Chest 0x02001149
- Antique Platter 0x020001F2
- Gilded altar box 0x0200096A
- Anvil 0x020011BF
- Large Golden Coin 0x02000172
- Renegade Chest 0x020010A4

#### Round 8 Chests and Keys (11-22)
Fixed:
- Forbidden Chest 0x0200109D
- Lunnum's Chest 0x02001268
- Lock Box 0x02000A7F
- Trunk of Bones 0x02000F03
- Puzzle Box 0x02000F33
- Vault Door 0x020011C5
- Treasure chest keys 0x02000160
- Shadow Chest and Vault keys 0x02000907
Sent back:
- Jaleh's Finery Chest (and the Armor and Magic Chests) 0x02000F30. Note: "Depth mapping is off - we should dump depth mapping and go more with just materials"

#### Round 9 (11-22)
Fixed:
- Bronze Lamp, and the Shrine of the Blood Pearl 0x0200010B: 0x05000278 0x05000285 0x05000E17 0x05000E5A 0x05000ECA 0x050010EB 0x05001A99 0x05001E38 0x050021D7 0x050021D8 0x050021D9 0x050021DA 0x05002357 0x05002358 0x050027D5
- Purple book 0x02000EF0: 0x05001AE0 0x05001AE1 0x05001AE2
- Fur bundle 0x02000E5D: 0x05000AE4
- Dark bottle 0x02000B1F: 0x05001C0B
- Lever 0x02001207: 0x05002503
- Gold horn 0x0200127E: 0x05002A12
- Small wooden stick 0x0200017B: 0x05000B41
- Rabbit Hutch 0x0200040F: 0x05001305
- Green jar 0x020005FC: 0x050017BD
- Blue book 0x02000EEF: 0x05000ACD 0x05000DFB
- Stone stand with a book 0x020011C2: 0x0500201C 0x05002514 0x05002515 0x0500276A 0x050027D7
- Treasure pile 0x02000EC4: 0x050003CA 0x050020B1
- Hooked pole 0x02000A41: 0x05002830
- Charred Falatacot Journal 0x0200105C: 0x050021D3 0x050021D4 0x050021D5
- Pale gem block 0x01000D86: 0x05000FA9
- Stone throne 0x02000931: 0x050019D3
- Woven column 0x020000E4: 0x05000AFA
- Plain gravestone 0x020016AE: 0x05002D43
- Creature remains 0x0200105E: 0x05001E06 0x05001E07 0x05001E08 0x05001E09
- Cut of meat 0x020000F7: 0x05000AF0 0x05000AF1
- Name banners 0x01002B49: 0x05001F37 0x05001F3B 0x05001F3C 0x05001F3D 0x05001F3E 0x05001F45 0x05001F48 0x05001FCC 0x05001FCD 0x05001FCE 0x05001FCF 0x05001FD2 0x0500204A 0x0500204B 0x0500204D 0x0500204E 0x05002050 0x05002053 0x05002054
Sent back:
- Dark stone column 0x0200085E: 0x0500275D 0x0500275F. Note: "Brick texture / relief map doesn't match the actual grout lines at all"
- Small dark piece 0x02000D3A: 0x05001F34. Note: "These look like just gray squares?"
- Kept: Heater shield on a wall 0x010002DB: 0x05000FDD; White crystal rock 0x02000CDA: 0x05001F4F; Dark stone door 0x0200098C: 0x05002733; Ursuin Rug 0x02000A94: 0x05001DFE; Dark floor runner 0x0100473A: 0x0500306B; Landscape banner 0x010036B0: 0x050026E3; Mountain banner 0x01000E76: 0x050026E4; Black stone block 0x02001A61: 0x0500303A; Black Spear Ice Totem 0x020015E5: 0x05002CBE; Brick pillar 0x02000AB0: 0x050027D6; Shard of the Eastern Pedestal 0x02001024: 0x05002819; Burun Mud-packed Chest 0x020010D7: 0x0500278D 0x050027E0; Black obelisk 0x020014FB: 0x05002C2B; Dark slab 0x02001AC8: 0x050030F2; Stone pillar 0x01003628: 0x050028E2 0x050028E9 0x05002912; Carved gravestone 0x020016B4: 0x05002D08; Spiked rail 0x020010A7: 0x0500272B; Dark floor plate 0x01003E68: 0x05002CC6 0x05002CCB; Black pyramid 0x020008E2: 0x05002764; Dark pyramid 0x020008DE: 0x0500269F; Pile of Rocks 0x02000FA2: 0x050027D2; Brick wall pieces 0x010041FD: 0x05002E12 0x05002E38; Wooden plank 0x01000BC9: 0x05002899; Wooden rack 0x02000919: 0x05002814 0x05002815; Arwic road sign 0x02000610: 0x050010EF; Brick wall panel 0x01003449: 0x05002708; Candle ring 0x020019E3: 0x05002F82; Jewelled rock cluster 0x02000AC8: 0x05001D84.

#### Round 9 Rework (11-22)
Fixed:
- Spiral 0x02000D3A: 0x05001F34
Sent back:
- Dark stone column 0x0200085E: 0x0500275D. Note: "We already have this texture relief mapped - but when it is in color - follow that"

#### Clear Maps (11-24)
Fixed:
- Wine bottle 0x02001288: 0x050026DB
- Bottle A (decanter) 0x020000A9: 0x05000A99
- Flask 0x020000AB: 0x05000A95
- Vial 0x020005FD: 0x05000F83
- Crystal lamp post 0x02000719: 0x05001401
Sent back:
- Champagne bottle 0x020012B6: 0x050025C3 0x050025C4. Note: "The label is semi fancy -  we need to do a better job tracing it"

#### Clear Maps Rework (not submitted)
Unmarked:
- Champagne bottle 0x020012B6: 0x050025C3 0x050025C4

#### Dom Pyrignon (11-24)
Fixed:
- Champagne in End of Retail 0x020012B6: 0x050025C3 0x050025C4
- Kept: Champagne in the 2005 world 0x020012B6-2005: 0x050025C3 0x050025C4.

#### Round 11 (11-25)
Fixed:
- Name banners, the rest 0x01002B44: 0x05001FCA 0x0500204F 0x05001F44 0x05001F38 0x05002051 0x05001FD1 0x05001F4A 0x05001F3F 0x05001FD3 0x05001F41 0x05001F43 0x05001F3A 0x05001FD4 0x05001F40 0x05001F39 0x05001F4B 0x0500204C 0x05001F46 0x05001F4C 0x05001F49 0x05001FD5
- Bunch of bananas 0x02000E5A: 0x05002068
- Black cage 0x020018F2: 0x05002EB7 0x05002EB8
- Green stone shrine 0x020014C3: 0x0500235D 0x0500250B 0x0500250D 0x0500250E 0x0500250F 0x05002511 0x05002513 0x0500250A
- Attunement Device Spring 0x02000D3D: 0x05001F35
- Purple swirl 0x0100043C: 0x05000376
- Lever 0x02001166: 0x0500242F 0x050024E6
- Steel star 0x02000140: 0x050002AC
- Green carved panel 0x02001201: 0x05002537 0x05002538 0x05002539
- Log ram on wheels 0x020010A6: 0x050027E2 0x050027E4
- Feast table 0x02001666: 0x05000DB7 0x050017AE 0x05001F5A 0x050025C5 0x05002BE0 0x05002BE1
- Snow drift with a hole 0x0200129C: 0x05002806 0x05002807
- Hidden Sho Festival Light 0x02000705: 0x050017AE
- Bloodied book on a stand 0x02000FAB: 0x050021D6
Sent back:
- Wine rack with a map 0x0200126A: 0x0500291A. Note: "Relief map is distorting this object."
- Cove Apple Wine bottle 0x0200016F: 0x05000A9A 0x05000A9B. Note: "Let's actually recreate this texture entirely. Make it a glass bottle with apple-cider color and a silver foil top."
- Black studded door 0x02001A97: 0x05002EB7 0x0500306C. Note: "Metal dots/studs should actually be raised above background metal"
- Ice wall 0x01004603: 0x05002FE1. Note: "Make this reflective solid ice material"
- Archery target 0x02000F31: 0x0500210F. Note: "Target colors are painted on top of wood texture, those, give it one consistent wood texture throughout"
- Framed painting 0x02000A22: 0x05001C31. Note: "Cracked stone painting - cracks should have relief map"
- Kept: Broken Menhirn Stone 0x02000C58: 0x050019A9; Portcullis 0x01002D1C: 0x050027F4; Stone bench 0x02001963: 0x05002EDE; Hide canopy 0x02000ABA: 0x05001D7A; Tied sack 0x02000F80: 0x0500216C; Stone arch 0x02000418: 0x05000E80; Snow heap 0x0200176D: 0x0500192D; Dark carved statues 0x0200126E: 0x05002700 (note: "Ensure metallic material").

#### Round 11 Rework (11-25)
Fixed:
- Cove Apple Wine bottle 0x0200016F: 0x05000A9A 0x05000A9B (painted anew by cider.py: apple-cider glass, a silver foil cap)
- Wine rack with a map 0x0200126A: 0x0500291A
- Black studded door 0x02001A97: 0x0500306C (studs proud, the door steel)
- Ice wall 0x01004603: 0x05002FE1 (polished, roughness 0.03; glacier ice was too blue)
- Archery target 0x02000F31: 0x0500210F (relief.py `painted`: the wood runs on under the paint)
- Framed painting 0x02000A22: 0x05001C31 (relief.py `:cracks`: level face, cracks sunk)
- Dark carved statues 0x0200126E: 0x05002700 (steel)

#### Red Crystal Obelisk (11-25)
Fixed:
- Red crystal obelisk 0x02000BBF: 0x05001E63 (its core seen through the shell's windows: the retail flames as clear crystal, clear 0.35, refraction 1.9, from a report at Darktide 0xA9AC; the developer asked for it less clear and more refractive than the Life Stone's 0.55 and 1.55)
Sent back:
- The same core painted anew as an ember crystal (a second option, not taken).

#### Round 12 (11-25)
Fixed:
- Attunement Device Gear 0x02000D3B: 0x05001F36
- Kitchen table 0x02001001: 0x050017A8
- Pile of armour 0x02001311: 0x0500284F. Note: "Ensure metal material"
- Green slime pool 0x02000DA9: 0x050029F8. Note: "Looks good, but also make sure any ground tiles of same texture match. Ensure slime-like gloss material"
- Green stone statue 0x02000D54: 0x05001F75 0x05002A69 0x05002A6B 0x05002A6C 0x05002A6D 0x05002A6E
- Stone double door 0x02001541: 0x05002AAB. Note: "Ensure metal material"
- Red bull banner 0x02001519: 0x050022D3 0x050022D4 0x05002C37 0x05002C38
- Bow 0x01003465: 0x05001F8C 0x050024D5
- Crossbow 0x01003468: 0x05001F8C 0x0500200B 0x050024D5 0x050024DA
- Ruschk Totem 0x020012A1: 0x050026EE. Note: "Ensure ice material"
- Golden drake 0x020011D0: 0x05001955 0x05001956 0x05001957 0x05001958 0x05001959 0x0500195A 0x0500195E
- Lamp post with a blue lantern 0x02000707: 0x05000E99
Sent back:
- Lava floor 0x02000E68: 0x05001824. Note: "We need to make sure this works and glows looks like the landscape lava ground tile"
- Painted cabinet 0x02000EFE: 0x050020E5 0x050020E6. Note: "Apply heavy relief map to items on shelf to give them some depth."
- Kept: Arched root 0x01004DA9: 0x05003318; Stone block with a green slab 0x020010A5: 0x050026E6; Snowy rock slab 0x01003909: 0x0500293D; Gnome statue 0x02000A98: 0x0500284D; Grey-blue floor patch 0x02000BF4: 0x05000ABF; Black sack 0x02000F7E: 0x0500216E; Red sack 0x02000F82: 0x0500216A; Low stone wall 0x010000D5: 0x05002794; Stone well 0x010041F7: 0x0500294F; Bone fan 0x0200159E: 0x05002173 0x05002175; Dark octagonal platform 0x020018C5: 0x05002EB0; Broken Fishing Pole 0x01002DE6: 0x050017F8 0x050018DF; Dark red pyramid 0x020005A8: 0x05001210; Bone polearm 0x0200107B: 0x050029FD.
- Notes applied: the armour pile wholly steel; the slime glaze=0.05 (its picture is on four slime pieces and no floor). The totem was already ice-polished (glaze 0.05) and the door's iron doors already iron.py metal.
- Left out: the Wheel of Fortune 0x02000C3F (draws nothing) and a snowy fir 0x02000BC9 (plants).

#### Round 12 Rework (11-25)
Fixed:
- Lava floor 0x02000E68: 0x05001824 (grit=lava: the clay grit made Pyreal draw it as stone, so its molten cracks did not glow; grit.py gained a lava tile)
- Painted cabinet 0x02000EFE: 0x050020E5 0x050020E6 (shaped by hand by shelves.py after three tries: light-shaped shelves were "entirely wrong"; the second missed the border behind the chest and the leaning book; the third the middle shelf's leaning books and squat candle)

#### Bookshelves (11-25)
Fixed:
- Wooden bookcase 0x02000183 (and 0x02000C56): 0x05000B15
- Stone-framed bookshelf 0x0200096C: 0x05001A3E (no material before)
- Stone bookcase 0x02001205: 0x05001A3E
- Low bookshelf 0x02000BAF: 0x05000B15
- The two pictures paint the same books, so shelves.py shapes them from one hand-placed list: about 60 uprights, three leaning, two large tomes lying on the top shelf and three books lying across the rows. The wooden frame has its grain, twelve domed bolts and iron corner plates. A search of every shelf-shaped model (375 pictures) found no other bookshelf picture. Three pages: the first had the lying books wrong and no frame relief; the second took the tomes for three books.

#### Red Crystal Obelisk Turn (11-25)
- Red crystal obelisk 0x02000BBF: 0x05001E63 takes round=45 (relief.py leans its normal 45 degrees at each side of the picture). The developer saw what the clear core shows jump each quarter turn as the obelisk spins: each flat face of the four-sided core bent the world behind it by one fixed amount. Its four identical faces are retail's.

#### Red Crystal Obelisk Points (11-25)
- Red crystal obelisk 0x02000BBF: its two points 0x05001E5F and 0x05001E62 drawn flat, as retail draws them (the End of Retail materials and 0x05001E62's 2005 one dropped). Its default animation 0x030008E7 turns it 88.5 degrees in 59 steps of 1.5 and loops, relying on four faces that look alike; on its points every other face shows the picture mirrored, and their relief lit each mirrored face from the other side, so the obelisk jumped at every loop. The developer saw the jump in a test build after the round=45 change.

### Looked at and left alone

- Props with no depth-mapped picture: 895 of the 3,666 placed props (2,771 have one). Only depth-mapped props were put on cards. 516 of the 2,193 prop pictures have no height map.
- Left out of the prop survey on purpose: plants, armour and clothing, buildings, walls and floors (room review), the Bael'Zharon statue, the iron chest, the stone head and boulder (own threads). Pictures shared with walls or floors were left to the room review; large pictures that already read as grain were kept.
- Round 2: King's Crown water lily 0x020003D2 (plant). Ferns, flying birds and scenery rocks above round 1 stay with their own threads.
- Round 4: 0x02000C39 draws nothing visible; eight plants left out (listed under trees).
- Next in line: round 13 starts after rank 943 in props.tsv.
- The scan of every picture for colours End of Retail cut (2026-11-24) found 17 candidates; only the champagne was changed.
- 2005 pictures that borrow round 1's recipes keep their old materials; iron.py has no era support, so 2005's iron is not metal.

### What Pyreal draws with End of Retail's art (tables/drawn-as-eor.tsv)

Pyreal swaps these into 1999 and 2005 worlds, so the pack leaves the older materials out (3f2dfce1, 0a53e8ee, c1045fb5):
- 174 room pictures (later_rooms.rs PAIRS), 41 of them tinted; 127 older materials left out (125 of 2005, 2 of 1999).
- 76 prop models (later_models.rs MODELS), chosen one by one in the era-props review rounds 1-3 (13, then 16, then 18 families marked "EoR"): 0x01000007 0x01000075 0x0100007B 0x010002CE 0x01000345 0x0100058F 0x010005F5 0x01000677 0x01000692 0x01000695 0x010006E0 0x01000A2F 0x01000ADA 0x01000BB2 0x01001B29-1B2B 0x01001BB2 0x01002D1C 0x01002EF1-2EF2 0x01002EF6 0x010031AF 0x010034FA 0x02000040-0041 0x0200007C 0x020000F2 0x02000109-010A 0x02000144 0x02000165 0x02000180 0x020001B4 0x02000200-0201 0x02000222 0x02000224 0x02000276 0x020002FA 0x02000359 0x0200035F 0x0200039C-039D 0x020003B1-03B2 0x020003CC-03CD 0x020003D3 0x020003DE 0x02000469 0x02000486 0x020004DD 0x02000608 0x020006C1 0x020006FD-06FE 0x020007C3 0x020007E4 0x0200086E 0x0200091B 0x020009B4-09B5 0x02000A02 0x02000A23 0x02000A53-0A54 0x02000BA5 0x02000EE8 0x02000F9F-0FA0 0x02000FF7 0x0200105B 0x02001065 0x02001149 0x02001250
- Left out for models: 2005 0x05000E11 (worn only by 0x020002FA and 0x01000ADA) and 2005 0x050013F8, 0x050013F9, 0x050013FB, 0x050013FC (0x02000486).
- Also gone in 0a53e8ee: 293 relief.py materials that added no relief (220 EoR, 73 of 2005).

### Branches (all in archive/combined-before-squash-2026-11-21, content in 0.5)

prop-textures 86ea9006 (rounds 1-4, drawn-as-eor), prop-textures-5 d61b37a1 (rounds 5-6), prop-textures-7 458b4926 (rounds 7-8), prop-textures-9 c2f8acdb (round 9), prop-textures-10 cb0d2cab (round 10), crystal-clear ca109a27, haystack fe4d22ed, haystack-height d56c42df (these seven under refs/archive/branches, content in 0.5.4), fix/prop-relief 1c542739 (chest plates, head, boulder), fix/chest-retexture ba8c3feb (chest.py), feat/statue-stone e93132f2. 292e88f2 and its revert dfd70bc3 net to nothing. Worktrees: dereth-enhanced-environment-wt/prop-textures, prop-relief, chest-retexture, statue-stone.

Older branches, all in archive/pack-history-2026-11-18 and shipped in v0.3 (01eca88f), not unmerged work: feat/iron-door-sheen 9cad3f77, feat/book-relief 5b75e0d0, feat/arms-sheen 5979d0d7, fix/robe-no-sheen b0519de3.

## 4. Room and ground textures

Scope: relief.py materials for walls, floors, ceilings, roofs and ground, from `tables/recipes.tsv` (1,115 rows,
every End of Retail picture relief.py works on), `tables/recipes-2005.tsv` (15 rows, 2005 pictures with their own
layout) and, until 0.5, `tables/eras.tsv`. A row there is not a review: most rows are automatic. The reviewed set is below.
Review page "Relief Review";
survey in `pyreal/notes/review/relief-survey*` and review notes room-relief/ (textures.tsv, pictures.tsv, uses.tsv).

### Before the review rounds

| Work | Ids | Date, commit |
|---|---|---|
| Built surfaces as stone, every world picture given relief, older eras' own pictures (eras.tsv), ground.py Launch grounds | all relief.py materials | 11-14, efdcb967, 89eeba1e (0.1, 0.2) |
| End of Retail's own 20 ground pictures (19 grounds and road 0x05001458) given relief | ground-relief d5538422, now an unreferenced commit | 11-14, in v0.2 |
| Older eras lay End of Retail's ground: Launch grounds, ground.py and 2005 ground relief removed | | 11-14, 130e9441 (v0.3) |
| Flagstone floors in a plain grid (`grid`) | 0x05002630, 0x050026F7, 0x05002727, 0x05002799, 0x050028DC, 0x050028DF, 0x050028E8, 0x05002961, 0x05002A0C, 0x05002EA8, 0x050010F8 (the rows 4a398cef added) | 11-17, 4a398cef (fix/flagstone-grid, in v0.3) |
| Dungeon 0x0200 walls, floor, ceiling | 0x0500274E-2752; 2005 0x05001D2D-1D31 at 0x02000108 | 11-19, 8df74c94 |
| check_relief.py and refit.py pass | 31 EoR and 23 2005 maps changed; 2005 0x05001D2E, 0x05001D30, 0x05001D31 keep their own | 11-19, 9d3fe0d2 |
| Thatch, turf, painted sign | 0x050011EC, 0x05001205, 0x05002A7D (2005 0x0500213E) flat; 2005 0x050019DB keeps its own | 11-19, 026323c2 |

### Room relief rounds 1-24 (2026-11-19), biggest drawn area first

All 348 materials in the review set ended marked good: 296 End of Retail (182 dungeon, 99 outdoors, 15 room)
covering 98.8% of End of Retail's drawn relief area, and 52 2005 stand-ins that borrow a changed recipe.
Squashed as fc2e3227 (pushed as origin/fix/room-relief), history in archive/room-relief-history and archive/main-before-room-squash.

The 348, by where they are drawn most:
- eor outdoors (99): 0x05000DA7 0x05000DF5-0DF6 0x05001203 0x0500127E 0x0500145D 0x0500180A 0x050018A0 0x050018A5 0x050018AF 0x050018DB 0x050018DD 0x050018DF-18E0 0x05001C4A-1C4B 0x05001D89-1D8A 0x050025F2-25F3 0x050025F6-2600 0x05002602-2604 0x05002607-260D 0x0500260F-2611 0x05002614 0x05002688 0x05002695 0x050026FD 0x0500283C 0x05002872 0x05002886 0x050028AC 0x050028C0 0x050028D3 0x050028DE 0x050028EA 0x05002919 0x0500291F 0x05002929 0x05002936 0x05002953 0x05002979 0x0500297B-297C 0x0500297E 0x05002990 0x0500299E 0x050029A9 0x050029BE 0x05002A16 0x05002A3A 0x05002A6F 0x05002A7D 0x05002B7E 0x05002B80 0x05002B82-2B84 0x05002B86 0x05002B88-2B8C 0x05002B8E-2B90 0x05002C11 0x05002C14-2C16 0x05002EC2 0x05002ED5-2ED6 0x05003046 0x05003298 0x05003310 0x05003343 0x05003346
- eor dungeon (182): 0x05000E13 0x05000E21 0x05002615-2616 0x05002618 0x0500261B 0x05002621-262D 0x05002630 0x05002633-2634 0x05002639-263C 0x0500263F 0x05002642-2643 0x05002646-264A 0x0500264D-264F 0x05002653 0x05002656-2657 0x0500265B-265C 0x05002660-2663 0x05002666-2667 0x0500266A-266B 0x05002670-2673 0x05002675-2676 0x05002687 0x05002692-2694 0x05002696 0x05002699-269B 0x0500269D-26A4 0x050026A6-26AB 0x050026B1-26B2 0x050026C0 0x050026C7-26CA 0x050026E8-26EA 0x050026ED 0x050026F3-26F4 0x050026F7-26F9 0x050026FC 0x050026FF 0x05002703-270A 0x0500270E-2710 0x05002712-2713 0x05002715 0x0500271D-271F 0x05002724 0x05002726-2728 0x05002735-273C 0x0500273F 0x0500274B-274C 0x0500274E-2752 0x05002766-2767 0x05002769 0x05002770-2771 0x05002775-2776 0x0500277A 0x0500277D 0x05002781 0x05002783-2786 0x0500278A-278E 0x05002792 0x05002797 0x0500279C-279D 0x0500279F 0x050027A3 0x050027A9-27AA 0x050027BF 0x050027CB-27CF 0x050027D4 0x050027DD 0x050027DF 0x050027EC 0x050027F0 0x05002B5E 0x05002C54 0x05002CC7 0x05002CC9 0x05002CCB 0x05002E11 0x05002E38 0x0500303A 0x05003060 0x050030B7 0x050032A0
- eor room (15): 0x05000E5C 0x05001029 0x050011EC 0x05001205 0x0500189F 0x05001CB4 0x05002678 0x050026CC 0x050026F1-26F2 0x05002841 0x0500287C-287D 0x050028DD 0x0500297A
- 2005  (52): 0x050000C7 0x050001DB 0x05000ABF 0x05000BB7 0x05000BCD 0x05000D10 0x05000D34 0x05000D55-0D56 0x05000D5A 0x05000D5E 0x05000D7A 0x05000FAB 0x05000FAF 0x05000FBB 0x05000FF5 0x05001020 0x050010F9 0x0500121A 0x050012AC 0x050012D9 0x05001369 0x05001376 0x05001395 0x050013A0 0x050013F5 0x0500175D 0x05001776 0x05001779 0x05001A5F 0x05001C67-1C69 0x05001C71-1C72 0x05001C74 0x05001C76 0x05001C8C 0x05001C96 0x05001D2D 0x05001D2F 0x05001D53 0x05001F6D 0x0500213E 0x05002150 0x05002329-232A 0x0500232F 0x05002332 0x05002335 0x050023F9 0x05002541

Rounds that changed maps, from the developer's notes ("pre" = fixed before they saw it, from notes on similar pieces). Rounds
not listed (4, 5, 8, 10, 12, 16, 19, 24) were all good with no change. Saved verdicts with notes exist for rounds 16-23.
- R1: 10 EoR and 7 2005 recipes refitted (e1a692cd); recipes-2005.tsv started.
- R2: 0x050026F4, 0x05002785, 0x050028EA ledges; 0x0500264D; 0x050011EC one cloth; 2005 0x05000D7A, 0x05001C96.
- R3: 2005 0x05001C96 one textile.
- R6 pre: 0x05002695, 0x05002705, 0x05002618; 2005 0x05002332. R6: 0x0500287D, 0x050026FF, 0x05002706, 0x050026C8, 0x050026CA, 0x05001CB4, 0x05002678, 0x0500260C, 0x0500278B (half depth), 0x05003046; 2005 0x05001C72, 0x050013A3 (keeps its own masonry).
- R7: 0x050026C8 middle courses.
- R9 pre: 0x05002707, 0x05002703, 0x05002709, 0x05002693, 0x05002726; 2005 0x050010F9, 0x05002335. R9: 0x050027CB, 0x050027CC, 0x050026C7, 0x050026A9, 0x050026A8 (half depth), 0x050026F3, 0x05002656, 0x05002872, 0x05002766, 0x0500266B; 2005 0x05001C57 keeps its own wood.
- R11 pre: 0x050027CE, 0x05002708, 0x0500297B, 0x05002692, 0x05002622, 0x05002724, 0x05002696, 0x05002623, 0x050027D4, 0x0500260F; 2005 0x05001369, 0x05001C67, 0x05002329. R11: 0x05002692 (moss flat), 0x0500297C, 0x050026F2, 0x0500265B, 0x05002A6F, 0x0500271F, 0x0500278C, 0x050027DF; 2005 0x05001C71.
- R13 pre: 0x0500266A, 0x05002775, 0x05002776, 0x05002704, 0x050026C9, 0x05002624. R13: 0x05003298, 0x05002776, 0x05002694, 0x050029A9, 0x0500262C, 0x05002784, 0x05002786, 0x05002727, 0x050026B1, 0x050018A0, 0x05002783, 0x050027CF, 0x0500278D, 0x0500278E, 0x050026C0, 0x050026ED, 0x05002672, 0x0500264E; nine 2005 stand-ins.
- R14: 0x05003298, 0x050026B1, 0x050027CF; 2005 0x05001395, 0x05000D34, 0x05000FBB. R15: 0x050026B1 brick by brick; 2005 0x05001395.
- R17 pre: 0x05002667, 0x05002767, 0x05002653, 0x05002639, 0x0500270A, 0x05002710, 0x0500291F; 2005 0x0500175D. R17 (29 good, 12 notes): 0x050026A6, 0x0500297A, 0x05002675, 0x0500262D, 0x050027AA, 0x0500277A, 0x05002769, 0x0500261B, 0x050027BF, 0x05002630, 0x05002E38, 0x05002E11, 0x0500273C; 2005 0x05001C68, 0x0500121A.
- R18 (13 good, 1 note): 0x0500261B three steps.
- R20 pre: 0x050026FD, 0x050027F0, 0x050027CD, 0x050029BE, 0x0500263C, 0x050026B2, 0x05003060, 0x05002660, 0x05002728, 0x05002841, 0x050027A9; 2005 0x05000D5A, 0x050012D9, 0x05001376, 0x05001776, 0x0500232A, 0x0500232F. R20 (33 good, 13 notes): 0x050026FD, 0x050028DE, 0x05002676, 0x05002615, 0x050026F1, 0x0500297E, 0x05002797, 0x0500189F, 0x050018A5, 0x0500277D, 0x05002666; 2005 0x050012D9 (like 0x050027A9), 0x05001776, 0x05000BB7, 0x05000BCD, 0x05001C8C.
- R21 (12 good, 3 notes), R22 (1 good, 2 notes), R23 (2 notes): 0x05002666 grout; 0x050026F1 and 2005 0x05000BCD beam and brick band, now shaped like each other.

### Relief re-run (2026-11-20, f5ecccf8)

Every relief.py material nobody had reviewed was made again: 303 maps changed (247 EoR, 55 2005, 1 1999), 184 gained
a height. Nothing was marked reviewed. Reviewed materials were kept exactly; 18 whose new map rated worse kept their old.

### Ground rounds (2026-11-20)

- R25 (reworked in d9939878): 12 cards. Needs work: road 0x05001458 ("extra jagginess"), grasses 0x05001459, 0x05002F6F, 0x05001457, 0x05001C3A, 0x05001C3B ("heavy", "random noise"), semi-barren rock 0x0500145A ("smoother", grass where mossy), packed dirt and forest floor 0x05001465, 0x05001466 ("too intense"). Good: 0x0500145B, jungle tree 0x05002601 and fern 0x050025F5 cut-out maps.
- R26: the nine reworked, all good. Squashed in 3784f487 and v0.4.0 (1c972a27).
- Ice 0x05001468 and 0x05001900 kept flat on purpose (ground-relief notes).

### Dungeon rounds (2026-11-20)

- R27 (reworked in 35c2b94a): 40 cards. Good: 0x0500262E 0x0500263D 0x05002665 0x050026F5 0x05002729 0x05002730 0x05002732 0x0500273E 0x05002742-2743 0x05002749 0x0500274D 0x05002791 0x050027C1 0x050027D9 0x05002CC6 0x05002CC8 0x05002E12 0x0500305E. Needs work (21): 0x05002652 0x05002654-2655 0x0500266D 0x0500266F 0x050026B9 0x050026E7 0x050026F0 0x05002748 0x05002779 0x0500277C 0x05002798-279B 0x050027A7 0x050027B6-27B7 0x050027DA 0x050027DE 0x050027F7; the 5 2005 pictures that borrow their recipes followed.
- R28 (three reworked in 8fc664e0): the 21 reworked plus 2005 borrowers, all good except 0x0500277C, 0x0500279B and 2005 0x05000FAE. 2005 good: 0x05000CD6 0x05000D18 0x05001993 0x05001A62.
- R29: 0x0500277C 0x0500279B and 2005 0x05000FAE, all good.
- R30 (40 pieces, in 3784f487 and v0.4.0, no verdict found): 0x05002617 0x0500261A 0x0500264B 0x05002674 0x05002697 0x050026AC 0x050026D8-26D9 0x050026EB 0x050026F6 0x050026FE 0x05002711 0x05002714 0x05002725 0x0500272E-272F 0x05002734 0x05002741 0x05002744 0x05002746-2747 0x0500276A 0x0500276E 0x0500277E-2780 0x05002796 0x050027AC 0x050027AE 0x050027B0 0x050027C5 0x050027D3 0x050027F9 0x0500280D 0x0500281A 0x05002825 0x05002E36-2E37 0x0500305F 0x05003061. Six were fixed before review from notes on similar pieces (00df0844): 0x05002E37, 0x05002E36, 0x050026F6, 0x050027F9 (made like 0x050027F7), 0x05002711, 0x05002725; 2005 0x050010F5. Also before review (5daf4c6a): 0x0500305E (R27, good), 0x05002729 (R27, good). Verdicts sent 11-22: see the next section.

### Wall, floor and ceiling rounds 30-55 (2026-11-22 to 2026-11-25)

From round 33 the rounds cover dungeon cells, building interiors and building shells, biggest drawn area first, and
only pictures drawn on no prop: a picture also drawn on a prop is decided with that prop (section 3). From round 38
each new picture is first matched against every passed one, and a close match takes the passed recipe before review.
"Cards at" is the commit the round's cards were made from. Rounds 30-37 are in main as 838e3c80 (0.5.3), rounds 38-46
as 31edb14b (0.5.4), rounds 46-49 on fix/relief-47 (in pack main 8261c2b3), rounds 50-55 on fix/relief-50; the round commits are under `refs/archive/branches/` (fix-relief-rerun, fix/relief-38,
fix/relief-43, fix/relief-46). Dates are the dates the verdicts were sent; the developer's notes are verbatim.

- R30 (11-22, cards at 00df0844): 41 cards (40 EoR, 1 2005), new dungeon pieces. 21 good, 20 bad, reworked in c1a3a8fd.
  - Fixed before review: 0x05002725, 0x05002E37, 0x05002E36, 0x050026F6, 0x050027F9 (like 0x050027F7), 0x05002711.
  - Bad: 0x0500276A "This is small mosaic tile with moss or something growing on top"; 0x05003061 "This could use some mild texture that matches the highlights. Very mild though, it is almost textile"; 0x050027B0 "Too deep and heavy, this is soft/rounded brick"; 0x050026FE "Texture on bottom is too heavy and pitted. It should be smoother rock"; 0x05002617 "This is a 3 level step down texture - we've had them in the past"; 2005 0x050010F5 "Make it match 0x05002725"; 0x050026EB "Give this a mild texture, we've done a similar image in the past"; 0x050026D9 "This is weirdly inverted on the brick part. Grout lines are showing higher than bricks."; 0x050026D8 "Grout lines showing higher than brick - this is 2 tiles on top, 3 tiles on bottom stone bricks"; 0x05002796 "Not matching stone brick layout at all"; 0x05002825 "Too intense/heavy of a relieft"; 0x05002741 "Too heavy of a relief"; 0x0500277E "Bottom section - plaster/stone - is too intense of a relief"; 0x0500277F "This doesn't match the stone pattern at all. This is tiles with cracks"; 0x0500305F "Match 0x05003061"; 0x050027C5 "This is a frame around a deeper center section with stone in it."; 0x05002697 "This is a brick wall with a design element in the middle, but the green is moss covering it - moss should be on top."; 0x05002780 "Rework, this is a wood/plaster top (wood frame over plaster wall), and a brick pattern on the lower half"; 0x050027AC "This is a 3 tier step down brick. Top row is two bricks. Second row is an alternating triangle brick pattern. Third row is also alternating triangle bricks, but much larger triangles."; 0x050027D3 "Brick with inner relief in the middle. Borders top and bottom. Should have some relief".
- R31 (11-22, cards at c1a3a8fd): 21 cards (19 EoR, 2 2005), round 30's bad ones reworked. 19 good, 2 bad, reworked in bef79f95.
  - Bad: 0x050026FE "Stone area still way too pitted, it should be soft waves on this particular stone. Also, bolts on top should be elevated above other parts of top border"; 0x050026D9 "Top bar needs work, maybe just make it elevated above everything else".
- R32 (11-22, cards at bef79f95): 0x050026FE and 0x050026D9, both good.
- R33 (11-22, cards at 9abefb81): 40 cards (40 EoR: 18 dungeon, 9 interior, 13 building shell), new pictures. 24 good, 16 bad, reworked in 27517edf (with 7 2005 borrowers; four copy a passed near-identical picture).
  - Fixed before review: 0x050026FA (traced as rock), 0x050027F8 (like 0x050027F7).
  - Bad: 0x050029BF "This is like shale tile on top and a cement-like border with extra design elements on the bottom"; 0x05002F9D "This is stone with two riveted rails"; 0x0500299F "This is like stacked stone in a shale-like pattern, not straight lines"; 0x050029D5 "Bamboo with grass - we've already done a tile nearly identical to this one"; 0x05001209 "We've already done a tile nearly identical to this one"; 0x05002922 "The grout lines on this are actually grass sticking out from stone, so it should actually be higher than the stone"; 0x05002925 "This is like a cross weaved wicker pattern"; 0x0500285C "We've already done a nearly-identical item, find that"; 0x050026FB "Way too pitted, this should be rolling stone - look for the heaviest cracks"; 0x050027B4 "Too intense of a relief"; 0x05002A70 "Way too pitted. This is moss on top of a realtively smooth stone with a few cracks"; 0x05002777 "Invented extra grout lines, this is a set of 8 bricks in various orientations, some have cracks"; 0x050027D1 "This is nearly-identical to others we have done - too intense of a relief, look for others"; 0x05002A63 "Simple checkerboard pattern, relief too intense, doesn't match near-perfect squares"; 0x05002874 "Top wood is an upside down bracket shape on top."; 0x05000D9B "This is a bamboo frame around a paper door/window".
- R34 (11-22, cards at 27517edf): 23 cards (16 EoR, 7 2005), round 33's bad ones reworked. 21 good, 2 bad, reworked in 914a662d.
  - Bad: 0x05002874 and 2005 0x05001005 (its 2005 picture) "Still missing the top border - its a wood upside-down-wide-U shape."
- R35 (11-22, cards at 914a662d): the bracket wall 0x05002874 and 2005 0x05001005, both bad: "I'm going to give you a hint as to where the wood is". The developer sent two drawings of the wood (a thin upside-down U); reworked in d08af785 (the field below one flat height, the tile strip raised a little with relief.py `:tiles=K`).
- R36 (11-22, cards at d08af785): both bad, "Almost, bottom bricks are 3 uniform bricks"; reworked in 205fe379.
- R37 (11-22, cards at 205fe379): both good.
- R38 (11-22, cards at dc976ac4): the reverse lookup. Every remaining wall, floor and ceiling was matched against the 417 passed, and 31 near-identical ones took a passed recipe (30 EoR shown, with 8 2005 pictures that follow them; 2005's passed 0x05002541 kept as it was). 31 good, 7 bad, reworked in 1a828010.
  - Copied: 0x05002773 (like 0x05002B5E), 0x05002848 (like 0x050027A7), 0x05002C30 (like 0x0500263B), 0x05002A43 (like 0x0500285C), 0x05002A0C (like 0x05002799), 0x05002A21 (like 0x05002841), 0x05002930, 0x050027C7 (like 0x050027C5), 0x050027B2, 0x0500283E (like 0x0500273E), 0x05002961 (like 0x05002799), 0x05002720 (like 0x05002CC9), 0x05002A0A (like 0x050027DD), 0x05002A51 (like 0x05002693), 0x050028F5 (like 0x0500297A), 0x05002E92 (like 0x05002722), 0x05002669 (like 0x050027DD), 0x05002859 (like 0x05002693), 0x0500120D (like 0x05001209), 0x05000C3A (like 0x0500265B), 0x05002782 (like 0x05002618), 0x050027B5 (like 0x05002639), 0x05002897 (like 0x0500289A), 0x0500290E (like 0x0500277E), 0x050027B9 (like 0x05002791), 0x0500297F (like 0x0500297A), 0x050028C2 (like 0x050028C0), 0x0500283F, 0x05002A1E (like 0x05002A63), 0x050028E8.
  - Bad: 0x05002A43, 0x05002A51 and their 2005 pictures 0x0500193D, 0x05001943 "I'm confused - the picture is black and white?" (they are grey in retail's files; shown again unchanged with a card saying so); 0x05002897 and 2005 0x05001CF9 "Frame doesn't match actual wood region"; 0x050027B9 "Too rectangular, doesn't match rounded stone bricks".
- R39 (11-22, cards at 1a828010): 7 cards (4 EoR, 3 2005), all good.
- R40 (11-22, cards at 117453f6): 40 cards (40 EoR), new pictures. 34 good, 6 bad, reworked in 1723c5f3 (with 2005 0x05001BD6).
  - Fixed before review: 0x05002A2B and 0x05002723 (slab lines sunk as cracks), 0x050026B6 (traced as rock), 0x0500276D (like 0x0500276A).
  - Bad: 0x05002A60 "Too pitted / intense relief"; 0x050026B4 "Doesn't match grout lines"; 0x050027E5 "Grout lines don't match actual stone"; 0x05002932 "Way too intense of a relief"; 0x050029D4 "Doesn't match the half bamboo poles"; 0x05002A31 "Way too intense of a relief".
- R41 (11-22, cards at 1723c5f3): 7 cards (6 EoR, 1 2005), all good.
- R42 (11-24, cards at 2fd90b33): 40 cards (40 EoR), new pictures. 18 good, 22 bad, reworked in f8cd42e2 (with five 2005 borrowers).
  - Fixed before review: 0x05002813 (like 0x05002619).
  - Bad: 0x050029D7 "Doesn't match the bamboo borders/frame"; 0x05002962 "Doesn't match the stone interrior at all"; 0x050026C5 "Doesn't match the rounded brick shape well at all - some bricks are cracked"; 0x050018A3 "Doesn't match the brick / grout line (which is moss filled)"; 0x050027A5 "Too intense of relief - doesn't match bricks"; 0x050027A6 "Grout lines a bit too thick"; 0x05002716 "Top/bottom border should be higher"; 0x05001F6A "Relief map too intense"; 0x050027C9 "Tile in center doesn't match stone shape"; 0x05002877 "Relief map a little too intense"; 0x050026B7 "Needs remapping - the bricks are pretty uniform in the center, bottom tile doesn't match, and top wood with metal should be mapped better."; 0x050028C4 "Wood logs with sign hanging over it."; 0x05002A30 "Relief map way too intense. This one should be mild."; 0x05002965 "Stones are irregularly angled, needs entire remapping"; 0x050028F6 "Weird relief in the middle for no reason"; 0x0500265E "Wooden frame borders a deeper center region."; 0x05002847 "Tile lines don't map"; 0x050027AF "Bottom border doesn't make sense"; 0x05002790 "Needs to trace bricks better, they have odd shapes here"; 0x05002828 "relief too intsnse"; 0x05002658 "Bottom bricks don't match, the brick columns are offset"; 0x05002923 "This is grass that is growing ABOVE the tile line".
- R43 (11-24, cards at f8cd42e2): 27 cards (22 EoR, 5 2005), round 42's bad ones reworked. 22 good, 5 bad, reworked in 0ce2ab75.
  - Bad: 0x050027A5 "The grout lines don't line up with the bricks at all"; 0x05002716 "There is a detailed brick pattern in the center that needs to be mapped"; 2005 0x05001004 "Probably needs to match 0x05002877" (now `like=0x05002877`); 0x050026B7 "Beam on top should be above bricks below"; 0x05002658 "There is a raised beam on top that should be higher than everything below.".
- R44 (11-24, cards at 0ce2ab75): 5 cards (4 EoR, 1 2005). 3 good, 2 bad, reworked in 4e68c247 (each top beam the highest part, its brackets in it).
  - Bad: 0x050026B7 "Isn't the beam across the top still lower? It looks like it is darker on the height map"; 0x05002658 "OK, the top row is a beamp across the top. We should have minor relief in it for the metal brackets on the sides - but it should all sit taller than the stuff below it. Also, bottom bricks are not tiled correctly - trace the natural stones.".
- R45 (11-24, cards at 4e68c247): 0x050026B7 and 0x05002658, both good.
- R46 (11-25, cards at 5236ad89): 40 cards (40 EoR), new pictures. check_relief had rated 0x050027BC, 0x05002829, 0x050028C5, 0x050028ED, 0x0500296D and 0x05002981 poorly; they were shown as they were. 19 good, 21 bad, reworked in 6f7c14ba.
  - Fixed before review: 0x0500295D (like 0x0500295F).
  - Bad: 0x050028ED "Bottom needs to have more of the pattern detail"; 0x050027BC "This is a natural stone wall with a bottom baseboard style set of tiles"; 0x050028DB "Relief too intense"; 0x050026B8 "This has two steps of wooden beams at the top on top of a plaster wall cracked at the top. Stone tile baseboard at the bottom"; 0x05002865 "This look to be a single concrete border at the top that sits above the lower rows"; 0x050028F4 "Wood frames on top of plaster wall"; 0x05002970 "Should be roof tile shaped"; 0x05002EA9 "Grout lines do not match brick pattern"; 0x05002EAA "Grout lines do not match brick pattern"; 0x05002949 "Detailed natural stone texture with cloth overlays and detailed borders"; 0x050028EE "Frame relief doesn't match actual frame"; 0x0500295D "Wood border on top of plaster wall with natural stone tiles below"; 0x050027B8 "This added an extra relief line in the top wooden beam part."; 0x05002B99 "Board lines too thick. Drew relief depth through metal side hinges"; 0x05002812 "Looks like this applied wood texture to brick"; 0x0500295E "Doesn't follow natural stone lines"; 0x050028C9 "This is drawings on a stone wall with moss. Moss should be raised, but black/stone drawings should match wall level"; 0x0500296A "Wooden frame relief doesn't match frame size"; 0x05002829 "Wooden frames/beams with hay hanging below on top of stone."; 0x050018A2 "This is moss sticking out from stone brick. Moss should come higher than stone"; 0x050028C5 "This is wood with a metal border on bottom.".
- R47 (11-25, cards at 6f7c14ba): 27 cards (21 EoR, 6 2005), round 46's bad ones reworked. 24 good, 3 bad, reworked in c4d578dc. Brick walls 0x05002EA9 and 0x05002EAA laid one brick at a time (`ashlar:block` rects at the measured joints); top beams highest with all below set back; frames fitted to the picture's wood; relief.py gained `:red=K` (a red-brown metal band proud, for 0x050028C5) and `:green=K` (moss greener than red proud, so yellow ochre is not taken for moss, for 0x050028C9). The 2005 borrowers 0x05000FED, 0x05001020, 0x05001DE7 and 0x05001C5B follow their recipes; 0x05000C4C takes `like=0x050028F4` (its yellow plaster read as wood) and 0x05000BFA has its own row (boards below the frame where End of Retail has stones).
  - Bad: 0x05002EA9 "The edge bricks (horizontally) don't seem to get relief appropriately"; 0x05002EAA "The edge bricks (horizontally) don't seem to get relief appropriately. Top brick pattern not represented correctly."; 0x05002829 "Hay relief pattern should follow the strands of the hay". The edge bricks had lost every joint (their halves were `:open`); relief.py gained `:seam`, which drops only the crease along the picture's own edge.
- R48 (11-25, cards at c4d578dc): the three reworked. 0x05002EAA's ten upright top bricks laid one by one; 0x05002829's hay shaped from its strands (`design:d=2.5`). 2 good, 1 bad, reworked in c83b9439.
  - Bad: 0x05002829 "Still some vertical line/jump happening about 2/3rds the way down" (where the hay part met the stone part; now one `design` part from the beam down).
- R49 (11-25, cards at c83b9439): 0x05002829 alone, good.

- R50 (11-25, cards at d05b0109): 40 cards (40 EoR), new pictures. 19 good, 21 bad, reworked in a0e4d1ba.
  - Fixed before review: 0x05002941 (like 0x050028DB), 0x05002A0D (like 0x050027C9). Shown as glossy ice with no relief (from the ice gloss): 0x0500280E, 0x0500280C, 0x0500280F, 0x05002473, 0x05002476, 0x05002477, 0x05002810, 0x05002478, all good.
  - Bad: 0x05002A2A "Relief is too intense/heavy"; 0x05002A17 "Relief not following natural stone shape"; 0x05002A32 "Relief is too intense/heavy"; 0x05002960 "This is a plaster wall with a wooden frame"; 0x05002A33 "Relief is too intense/heavy"; 0x05001E74 "This is a tile wall - ignore shadow/dark area for relief as that is like smoke on the wall - we should map to grout lines"; 0x05002A0D "Relief does not map to top beam and lower studded metal panels."; 0x050028CD "This relief map has some weird harsh line divisions"; 0x05002A4A "Relief is too intense/heavy"; 0x0500294A "Plaster wall has detailed design borders that should be mapped better"; 0x05002943 "Outer pillars should be higher than center region"; 0x05002631 "Inconsistent relief mapping on vertical tiles (which are rounded like roof tiles)"; 0x0500290D "Center beam should be higher than other areas"; 0x05002991 "Relief is too intense/heavy. Doesn't map to image well"; 0x050028DC "Relief is too intense/heavy"; 0x05002E3C "Relief is too intense/heavy and pitted"; 0x05002968 "Doesn't map to wood frame over plaster wall"; 0x050027BB "Doesn't map to border tiles"; 0x05002A5D "Don't relief center areas, just make entire thing one consistent textile texture"; 0x050028DA "Doesn't map to beam in center and right side"; 0x05002976 "Doesn't map to wood frame and stone and brick tiles".
- R51 (11-25, cards at a0e4d1ba): 29 cards (21 EoR, 8 2005), the last round's bad ones reworked. 26 good, 3 bad, reworked in 74283922.
  - Bad: 0x05002A0D and 2005 0x05000E86 "The bottom two thirds, the very far left and right, are the brick texture, not part of the frame"; 0x05002943 "There is texture and relief on those side columns, and they flute out on the top".
- R52 (11-25, cards at 74283922): the three reworked: brick at 0x05002A0D's outer edges behind narrower metal posts; 0x05002943's gold columns carved (`design:d=6`) with flared capitals. 2 good, 1 bad, reworked in 139f78ef.
  - Bad: 0x05002943 "Still not mapping well to the gold columns on the sides".
- R53 (11-25, cards at 139f78ef): 0x05002943 alone: the columns' carving deepened and their flared bases added. Bad, reworked in e66ef1d4: "Look at the darkest/black edges near the column relief - those don't belong there" (the shadow painted beside each column read as a groove; that strip is now level, a small step below the column, all parts `:open`).
- R54 (11-25, cards at e66ef1d4): 0x05002943 alone. Bad, remade in 03bba45e: "You're getting worse. Start over, pay actual attention to what is going on here. Stop trying to throw random algorithms at this". Remade from what the wall shows: flat `cloth` (the scale pattern is printed, the shadow beside the columns painted), the carved rail `design:shade` proud of it, the gold columns `design:shade` highest.
- R55 (11-25, cards at 03bba45e): 0x05002943 alone, good.

Outside the rounds: the large square dungeon floor paver 0x05002629 (cell 0x019E010A) passed review traced as rock
but looked too heavy in play, so it became a flat paver with a fine grain and narrow joints (11-22, f6b0baa6, in 0.5.3).

### Sand (2026-11-20, d297e694)

End of Retail's yellow sand 0x0500145D takes the new sand recipe (was auto plaster), grey sand 0x0500145F remade.
Rendered at the developer's view at Morntide 0x7E62 and the Yaraq desert; merged into pack 0.4.4 (141f440b). 2005's 0x0500145D (128 px) not redone.

### Ice gloss (2026-11-25, fb3931c3)

The ice pictures with no material were drawn matte (ground ice as snow). Ground ice 0x05001468 and 0x05001900, the ice cave's
0x05002473, 0x05002476, 0x05002477, 0x05002478, 0x0500247B and the ice dungeon's 0x0500280C, 0x0500280E, 0x0500280F,
0x05002810 take roughness 0.3 with no relief (`glaze=0.3`, the ground still flat as passed); the 2005 and 1999 ground copies
changed only their roughness. Pyreal's own ice surface kind and reflections are on its branch review/ice-sheen. Shown to the
developer as renders, not yet as a review round.

### Not reviewed

- After round 55 (11-25), 667 End of Retail pictures are walls, floors and ceilings drawn on no prop: 449 passed
  (98.5% of their drawn area), 106 automatic relief.py materials (0.1%) and 112 with no material (1.4%). The order:
  the automatic ones by area, then the ones with no material. 95 more are also drawn on a prop and go with their prop.
- 2005's own 0x0500145D sand (128 px) was never redone (see Sand).
- Every other relief.py material (3,468 in the 0.5 manifest, minus the reviewed set above) is automatic and unreviewed, including what the re-run remade.
- 2005 and 1999 pictures except the stand-ins named above; the 0.5 squash dropped tables/eras.tsv rows for pictures Pyreal swaps (drawn-as-eor).

### Branches

All under `refs/archive/branches/` now; no relief branch or worktree is left.
- fix/room-relief fc2e3227 (also origin/fix/room-relief): rounds 1-24, in main.
- fix/relief-rerun 1c972a27 (= v0.4.0): re-run, ground, dungeon rounds 27-30; history in archive/relief-rerun-history 00df0844.
- fix-relief-rerun 205fe379: rounds 30-37 and the bracket, in 0.5.3 (838e3c80); fix-relief-next 838e3c80 is that release.
- fix/relief-38 2fd90b33 (rounds 38-42), fix/relief-43 4739cb1b (rounds 43-45, round 46's prep), fix/relief-46 0016adf2
  (the paver and crystal merges): in 0.5.4 (31edb14b).
- sand-waves d297e694: in archive/pack-history-2026-11-21 and main.
- fix/flagstone-grid 4a398cef: in archive/pack-history-2026-11-18, shipped in v0.3.

## 5. Every branch and tag, and where its work is

| Ref | Tip | Held | Where the content is now |
|---|---|---|---|
| main, combined | fbaee071 | 0.5 release: four squash commits a95f7082, 1e0b6b0f, 547c3224, fbaee071 | main |
| archive/combined-before-squash-2026-11-21 | b8d0607c | everything that went into 0.5, unsquashed (68 commits) | 0.5 |
| archive/pack-history-2026-11-21 | 141f440b | old main, 0.4.4: v0.4.0 plus sand-waves and trunk-taper | 0.5 |
| archive/pack-history-2026-11-18 | d8784515 | pre-squash 0.3: flagstone grid, books, iron doors, arms, robe sheen, eor-ground | v0.3.0 01eca88f |
| archive/main-before-room-squash | efe73ae0 | room relief rounds 1-11 | fc2e3227 |
| archive/room-relief-history | 47778c6b | room relief rounds 1-23, 26 commits | fc2e3227 |
| archive/relief-rerun-history | 00df0844 | re-run, ground, dungeon rounds 27-30 | 3784f487, v0.4.0 |
| v0.1.0, v0.1.1, v0.2.0, v0.3.0, v0.4.0 | 275d4c4d, 3c94fb6b, 89eeba1e, 01eca88f, 1c972a27 | releases | |
| origin/main (as last fetched) | 1c972a27 | 0.4.0 | |
| origin/fix/room-relief, fix/room-relief | fc2e3227 | room rounds 1-24 | main |
| fix/relief-rerun | 1c972a27 | as v0.4.0 | main |
| archive/branches/fix-relief-rerun | 205fe379 | relief rounds 30-37, the bracket | 0.5.3 (838e3c80) |
| archive/branches/fix/relief-38 | 2fd90b33 | relief rounds 38-42 | 0.5.4 (31edb14b) |
| archive/branches/fix/relief-43 | 4739cb1b | relief rounds 43-45, round 46's prep | 0.5.4 (31edb14b) |
| archive/branches/fix/relief-46 | 0016adf2 | paver 0x05002629, crystal and giant tree merges | 0.5.3 and 0.5.4 |
| fix/armor-relief | a6448419 | armour 3-4, clothing 1-5 | 0.5 |
| armor-relief-presquash | 420a824a | armour 1-2 unsquashed | same armour files as 6b7ec972 |
| armor-r3-presquash | 4d26ddbc | armour 3 unsquashed | same tree as 1cf20584 |
| era-props | 018f49fe | older-era plant models | 0.5 |
| era-props-trees | e318f41e | tree rounds 1-4, trunk fits | 0.5 (fits later dropped) |
| era-props-trees-sway | 51d3065d | four `[[sway]]` entries | 0.5 |
| tree-picks | c98a22b3 | keep picks, rounds 5-8 | 0.5 |
| tree-rollback-044 | 15ec42da | round 9 | 0.5 |
| tree-birch-044 | 703efe54 | round 10 | 0.5 |
| trunk-taper | d849fff5 | taper_trunks.py for 4BE, 12FF | 0.4.4, 0.5 |
| sand-waves | d297e694 | sand recipe | 0.4.4, 0.5 |
| prop-textures | 86ea9006 | prop rounds 1-4, drawn-as-eor | 0.5 |
| fix/prop-relief | 1c542739 | chest plates, stone head, boulder | 0.5 |
| fix/chest-retexture | ba8c3feb | chest.py | 0.5 |
| feat/statue-stone | e93132f2 | solids.py statue | 0.5 |
| feat/iron-door-sheen | 9cad3f77 | iron doors, softer | v0.3 |
| feat/book-relief | 5b75e0d0 | Academy books | v0.3 |
| feat/arms-sheen | 5979d0d7 | arms.py | v0.3 |
| fix/flagstone-grid | 4a398cef | flagstone grid | v0.3 |
| fix/robe-no-sheen | b0519de3 | Ethangar's Robe silk removed | v0.3 |
| (no ref) d5538422 | | ground-relief, 2026-11-14: EoR's own 20 ground pictures | v0.2 content; commit is unreferenced and can be garbage-collected |

None of the local branches holds work missing from 0.5 or an earlier release. The branches named as never
merged (feat/arms-sheen, feat/book-relief, feat/iron-door-sheen, fix/flagstone-grid, fix/robe-no-sheen,
armor-r3-presquash, armor-relief-presquash) were squashed into a release, so `git branch --merged` doesn't list them.

## 6. Where the full history lives

- Every pre-0.5 commit, with messages naming each id, round and note, is kept in the local repo under hidden refs
  `refs/archive/*` (`git log refs/archive/tags/pack-history-2026-11-21`; `git for-each-ref refs/archive` lists them).
  Each old branch's tip is `refs/archive/branches/<name>`.
- `tables/armor.tsv`, `tables/recipes.tsv`, `tables/recipes-2005.tsv`, `tables/drawn-as-eor.tsv`,
  `tables/retail-trunks.txt`, `pack/manifest.toml` and `pack/trees/` in this repo.
- The review pages, saved verdicts and surveys are kept with Pyreal's review notes.
