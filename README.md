# Switchboard Test

**Open hardware, firmware and software for an operant paradigm assessing sequential spatial memory in rats.**

This repository accompanies the paper:

> Sahu R, Maćkiewicz K, Tkachenko D, Żakowski W, Domkowicz K, Polniak O, Kaźmierska-Grębowska P, Wiśniewski D, Kotus J, Niediek J, Aggleton JP, O'Mara SM, Jankowski MM. **A quantitative operant paradigm for assessing sequential spatial memory in rats.** *(in preparation)*

Representative session data: [doi.org/10.6084/m9.figshare.31034230](https://doi.org/10.6084/m9.figshare.31034230)

---

## About the Switchboard Test

The Switchboard Test is a low-cost, modular open-field arena in which rats learn to press floor buttons of a 3 × 3 array in a fixed spatial order (for example 7 → 4 → 2) to obtain food pellets. Guided by button lights during acquisition, rats learn to reproduce the sequence from memory, so that accuracy, errors and timing of every response can be quantified trial by trial.

- **Real-time control:** an Arduino Mega 2560 runs the task as a non-blocking state machine and timestamps every event with 1 ms resolution.
- **Host software:** a Python application configures protocols, plays the auditory cues, controls video recording (OBS Studio) and logs all events to CSV.
- **Synchronisation:** every button press, reward and error is also available as a 2 ms TTL marker for electrophysiological recording or stimulation systems, and two LEDs mark trial onsets and a 2 Hz reference in the video.
- **Modular design:** the interactive floor and wall can be removed or replaced with blank parts, so recordings can be made in the full task environment or in an empty open field with the same geometry.
- **Configurable:** sequences, guidance, reward size, sounds and session length are set as named protocols, without changing the firmware.

## Repository contents

| Folder | Contents |
|---|---|
| [`firmware/`](firmware) | Arduino Mega 2560 firmware |
| [`software/`](software) | Python control application (GUI) and protocol file `config.json` |
| [`hardware/laser_cut/`](hardware/laser_cut) | CorelDRAW files (with PDF exports) for the laser-cut acrylic parts: arena, interactive floor, interactive wall, transparent cover and shaping box |
| [`hardware/3d_print/`](hardware/3d_print) | STL files for the 3D-printed parts: electronics enclosure, LED-matrix and speaker mounts, amplifier and DC-socket mounts, cable holder, reward track, Axona TTL adaptor |
| [`hardware/cad/`](hardware/cad) | Full 3D model of the apparatus |
| [`hardware/electronics/`](hardware/electronics) | Wiring and pin assignment |
| [`figures/`](figures) | Plotting scripts, plot data and figures of the paper |
| [`docs/`](docs) | Photos and documentation |
| [`example_data/`](example_data) | Example session files |

Some folders are still being filled and will be completed with the release accompanying the paper.

## Getting started

**Hardware.** Cut the acrylic parts from `hardware/laser_cut/` (3 mm acrylic), print the parts in `hardware/3d_print/`, and assemble as described in the Methods of the paper. Main components: Arduino Mega 2560, nine 60 mm arcade push buttons with LEDs, Adafruit DotStar 8 × 8 LED matrix, Campden Instruments 45 mg pellet dispenser, loudspeaker with amplifier, and two DB25 breakout boards.

**Firmware.** Open `firmware/switchboard_firmware/switchboard_firmware.ino` in the Arduino IDE or Arduino Cloud Editor, install the *Adafruit DotStar*, *Adafruit DotStarMatrix* and *Adafruit GFX* libraries, select *Arduino Mega or Mega 2560* and upload.

**Software.** Requires Python 3.12 (tested on Windows 10).

```bash
pip install -r requirements.txt
python software/switchboard_control.py
```

Keep `config.json` in the same folder as the program and set the sound-file paths to your own files. Select the Arduino's COM port (19,200 Bd), choose a protocol, enter the animal ID and session number, and start the session. For automatic video recording, enable the WebSocket server in OBS Studio and enter its password in the program if authentication is used.

## Data output

Each session is saved as one CSV file named `SessionLog_RatID_<animal>_<DDMMYY>_Session_<n>_Date_<YYYY-MM-DD>.csv`. It starts with header rows (animal ID, session number, date, protocol name and full configuration) followed by one row per event — trial start and end, button press and release, sounds, sequence completion, reward and pellet delivery — each with a controller timestamp in milliseconds.

## Licence

- **Code** (`firmware/`, `software/`, scripts in `figures/`): [MIT License](LICENSE)
- **Hardware design files, figures, documentation and data**: [CC BY 4.0](LICENSE-CC-BY-4.0.md)

## Citation

If you use the Switchboard Test, please cite the paper above. Citation details for this repository are in [`CITATION.cff`](CITATION.cff) (GitHub: *Cite this repository*).

## Funding

This research was funded by the National Science Centre, Poland (NCN), under the POLONEZ BIS 3 programme, grant no. 2022/47/P/NZ4/03358. The POLONEZ BIS programme has received funding from the European Union's Horizon 2020 research and innovation programme under the Marie Skłodowska-Curie grant agreement No. 945339. This research was also funded by the IDUB Platinum programme of Gdańsk University of Technology, grant no. 1/1/2024/IDUB/I.1B/Pt.

## Contact

**DeepBrainLab**, BioTechMed Center, Multimedia Systems Department, Faculty of Electronics, Telecommunications and Informatics, Gdańsk University of Technology, Poland — [www.deepbrainlab.com](https://www.deepbrainlab.com)

Corresponding author: Maciej M. Jankowski (macjankow@gmail.com)
Repository maintainer: Ravindra Sahu (ravindra.s0793@gmail.com)
