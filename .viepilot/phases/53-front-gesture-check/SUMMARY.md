# SUMMARY — Phase 53: front gesture upload check (BUG-049)

- 53.1: gesture head check now asks whether the reference head keeps its own pixels (`GESTURE_HEAD_KEPT = 0.75`), measuring head top/centre inside the reference head only. A hand raised beside the shoulder or face (count, think, wave) no longer counts as a changed head; a redrawn or moved head is still refused.
- 53.2: a refused upload shows `Not stored: <reason>` on its own card.

Full pytest 1890 passed in 1032.11s (4 new tests); 15 approved front pictures still pass under the new rule.

Pending: owner retries Lina's count-1/count-2 pictures on an app running this code (source launch or an owner-authorized EXE update). Unblocks 49.10.
