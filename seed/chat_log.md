# trailnet-lab channel, Oct 26 to Oct 30, 2026

Messages posted by the lab during the seed week. All times Mountain. Used to seed the room history on build day, or read directly by the Reporter if seeding is not possible.

```
[2026-10-26 08:12] Priya Nair: Group meeting at 10 in 3412. Agenda: model size, PIR false triggers, labeling questions, eval dashboard, the Dec 1 workshop call. Wei goes first-ish since they leave early.
[2026-10-26 08:40] Lucas Moreno: Deep sleep is working on the node. 0.4 mA between triggers, was 11 mA. Details in the meeting.
[2026-10-26 09:55] Sofia Alvarez: Manifest is at 2,900 frames. 1,900 empty, 620 deer, 180 elk, 70 coyote, 130 other. Yes, coyote is 2 percent. We will talk about it.
[2026-10-26 10:31] Priya Nair: Meeting done, transcript will be posted when the export finishes. Short version: Dec 1 workshop deadline is on, five classes plus a partial flag, I try distillation, Lucas benchmarks new modules Friday, Sofia writes the labeling guideline by Wed.
[2026-10-26 11:45] Wei Zhang: Added the night/day holdout split definition to the repo under model. Night frames are stratified by site. Heading to the airport, at the conference Tue through Thu, will read the channel evenings.
[2026-10-26 13:30] Lucas Moreno: PIR debounce is in. Single short pulses no longer trigger a capture.
[2026-10-26 15:02] Omar Haddad: Dashboard layout proposal is in the eval README. Three panels: weekly accuracy day/night, per-class recall, confusion matrix. Priya, the CSV columns are there too.
[2026-10-26 16:50] Lucas Moreno: Power budget spreadsheet is in firmware/. With the current trigger rate at the river site the battery lasts 6 weeks, not 4 months. The false triggers are eating it.
[2026-10-27 09:05] Sofia Alvarez: 200 more frames labelled this morning, mostly the Saturday river batch. Manifest v0.2 pushed.
[2026-10-27 09:35] Lucas Moreno: Deep sleep committed. Next is the capture path, which I can only half test until the IR-cut modules arrive.
[2026-10-27 10:15] Priya Nair: Training script is in model/. It writes the eval CSV Omar asked for. Columns: week, split, day_accuracy, night_accuracy, model_kb.
[2026-10-27 11:20] Lucas Moreno: Capture stub is in with an ir_cut flag so the night path is ready for the new modules.
[2026-10-27 13:45] Sofia Alvarez: Found and fixed an off-by-one in the manifest writer. The last frame of every batch was being dropped. About 15 frames recovered. Sorry.
[2026-10-27 15:10] Lucas Moreno: Firmware README with wiring and the pin map is up for whoever builds the second node.
[2026-10-27 17:40] Lucas Moreno: Simulated the two-pulse trigger on Saturday's river log. It would have removed 180 of the 290 empty triggers. One third of the false triggers remain, probably the big grass movements. Trigger timestamps now logged to SD so we can keep doing this.
[2026-10-27 20:10] Wei Zhang: Reading from the hotel. Lucas, 180 of 290 is great. Priya, if distillation helps night, I want to see the per-site breakdown, not just the total.
[2026-10-28 09:10] Sofia Alvarez: Labeling guideline v1 is in data/. Dr. Chen, can you review the scheme before I start relabeling? @Maya Chen
[2026-10-28 09:50] Maya Chen: Reviewed. Add a line about antlers in shadow, otherwise approved. Go ahead.
[2026-10-28 10:40] Priya Nair: Distillation result. Student at 240 KB after int8. Day 88 (was 89), night 74 (was 71). Night test set is only 60 frames so take the 74 with salt. Details at the 2 pm sync.
[2026-10-28 11:25] Sofia Alvarez: 180 frames flagged as partial. 140 deer, 12 coyote, rest elk. Relabel pushed.
[2026-10-28 14:25] Priya Nair: Sync done. Decision: dataset v0.3 is frozen for the workshop paper, splits by site, test set is the ridge site. @Maya Chen you said to bring a freeze proposal, we went ahead since you were travelling. Say so if you object.
[2026-10-28 14:40] Omar Haddad: Eval scripts are in eval/. weekly accuracy plot and confusion matrix from the CSV.
[2026-10-28 15:05] Omar Haddad: Papers as promised. The camera-trap one: https://arxiv.org/abs/1703.05830 and the on-device one: https://arxiv.org/abs/2007.10319
[2026-10-28 15:06] Omar Haddad: And the one my search turned up that is definitely not about us, posted for entertainment: https://arxiv.org/abs/2203.02155
[2026-10-28 16:20] Sofia Alvarez: v0.3 exported. 4,120 frames. Empty 2,640, deer 870, elk 260, coyote 110, other 240. 160 night frames in test. Manifest and split file in data/.
[2026-10-28 18:30] Maya Chen: No objection to the freeze. Good call to not wait. Lucas, any word on the modules?
[2026-10-28 19:05] Lucas Moreno: Vendor emailed at 5. Modules now shipping Monday Nov 2, not Thursday. So no capture benchmark Friday. I'm blocked on the capture path and the capture power numbers until they land. Working on the trigger logging and the second node build in the meantime.
[2026-10-29 09:20] Priya Nair: Quantize script pushed. It reports the int8 size against the 250 KB budget so nobody has to ask.
[2026-10-29 10:45] Sofia Alvarez: Class counts for v0.3 are now in the data README so they stop living in my head.
[2026-10-29 13:35] Omar Haddad: Related work draft has six entries, in paper/. Wei, the night and domain adaptation refs are yours when you're back.
[2026-10-29 15:05] Sofia Alvarez: Added 200 empty hard negatives from the windy days. These are the frames that fooled the PIR. If the model can learn "grass" we save Lucas's battery.
[2026-10-29 21:15] Wei Zhang: Back Friday afternoon. Will do the related work refs Monday as Omar said.
[2026-10-30 09:40] Priya Nair: Night test rerun on the v0.3 test split, 160 night frames. Student model: day 88.3, night 73.1. So the 74 held, roughly. Coyote recall at night is 41 percent, which is the number to beat.
[2026-10-30 11:10] Sofia Alvarez: Manifest validation script in data/. Run it before you push a manifest change. It checks the five classes, the partial flag and that no frame id is in two splits.
[2026-10-30 14:00] Maya Chen: Good week. Monday agenda: Wei's night plan now that we have 160 test frames, the "other" versus empty question Omar raised, and whether the module delay changes the paper. Have a good weekend.
```
