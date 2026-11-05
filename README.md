# Tabulate Alaska's rank choice voting
Parses and counts Alaska's Rank Choice Voting files.
Currently only parses `CandidateManifest.json` and `CvrExport.json`. The full `CvrExport.json` is too big for Github so only a `tempCvrExport.json` file is included in this repo

## Data Source
[Alaska Division of Election voting results](https://www.elections.alaska.gov/election-results/)
Downloaded the evening of 11/4/2026. The only file that should change as more absentee votes are received is `CvrExport.json` which, as described above, isn't included.

## How to run
1. Download and save an updated `CvrExport.json` into `data`
2. Specify the contest of interest in `voteTabulator.py` using the codes in `ContestManifest.json`
3. Run `voteTabulator.py`

