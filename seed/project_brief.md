# TrailNet project brief

Paste this into the room rules so every agent reads it.

```
TrailNet is a low-power smart camera trap that counts wildlife on the device. A passive-infrared motion sensor wakes a microcontroller, which captures a frame and runs a small image classifier. The node uploads only the animal class and count over a low-bandwidth radio, never the image.

Classes: empty, deer, elk, coyote, other. A separate partial flag marks frames where only part of the animal is visible. Partial is not a class.

Constraints: the quantized classifier must stay under 250 KB to fit the microcontroller's flash beside the firmware. Night frames are grayscale infrared and are the main accuracy problem. Coyote is about 2 percent of the data.

Workstreams and owners: camera node firmware and power budget (Lucas Moreno); frame collection, labeling and dataset versions (Sofia Alvarez); model training and quantization (Priya Nair, team lead); night infrared domain adaptation (Wei Zhang); evaluation dashboard and paper draft (Omar Haddad). PI: Dr. Maya Chen.

Deadline: workshop paper, December 1, 2026. Dataset v0.3 is frozen for the paper.

Repository: trailnet (path given below).
```

Word count: about 160. Trim the constraints paragraph if the Console rules field has a limit.
