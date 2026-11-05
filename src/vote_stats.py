# -*- coding: utf-8 -*-
"""
Created on Thu Nov  5 14:05:47 2026

@author: Nathan Green
"""
import os
import glob
import polars as pl
from vote_stats import parse_cvr_json
from vote_stats import parse_candidate_json



if __name__ == "__main__":
    data_path = os.path.join("..","data")
    cvr_files = glob.glob(os.path.join(data_path,"CvrExport*.json"))
    candidate_file = os.path.join(data_path,"CandidateManifest.json")
    
    # You will need to look at the JSON file to find the specific "Id" for the contest you want to tabulate.
    contest_id_to_tabulate = 5 
    print("Parsing Candidates...")
    try:
        candidates = parse_candidate_json(candidate_file, contest_id_to_tabulate)
        print(f"Found {len(candidates)} valid candidates in contest.\n")
    except FileNotFoundError:
        print(f"Error: Could not find {candidate_file}. Continuing with only candidate IDs.")
    print("Loading and cleaning ballots...")
    try:
        election_ballots = []
        for file in cvr_files:
            election_ballots = parse_cvr_json(file, contest_id_to_tabulate, election_ballots)
        print(f"Loaded {len(election_ballots)} valid ballots.\n")
    except FileNotFoundError:
        print(f"Error: Could not find {file}. Please ensure the CVR JSON is in the same directory.")

    ballots = pl.Series("Votes", election_ballots)
    ballot_counts = ballots.value_counts(sort=True)