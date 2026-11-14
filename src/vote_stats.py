# -*- coding: utf-8 -*-
"""
Created on Thu Nov  5 14:05:47 2026

@author: Nathan Green
"""
import os
import glob
import polars as pl
from voteTabulator import parse_cvr_json
from voteTabulator import parse_candidate_json

def bullet(candidate_id):
    """
    Returns logical expression for polars dataframe to specify rows where the 
    column "Votes" is a list with a length of one and a value equal to 
    candidate_id.
    """
    return ((pl.col("Votes").list.len() == 1) & 
            (pl.col("Votes").list.first() == candidate_id))

def exact_round(candidate_id, round_no=0):
    """
    Returns logical expression for polars dataframe to specify rows where the 
    column "Votes" is a list with a value equal to candidate_id at index round_no.
    If  round_no exceeds the index, it returns Null
    """
    return pl.col("Votes").list.get(round_no, null_on_oob=True) == candidate_id

def a_before_b(ballot, a, b):
    """
    Returns boolean True if a occurs before b in list ballot or if a is in the 
    list but b is not
    """
    if a in ballot and b in ballot:
        return ballot.index(a) < ballot.index(b)
    return a in ballot and b not in ballot

def ranked_ahead(id_a, id_b):
    """
    Returns logical expression for polars dataframe to specify rows where 
    column "Votes" is a list that contains id_a and id_a occurs before id_b if 
    id_b is present
    """
    return pl.col("Votes").map_elements(lambda x: a_before_b(list(x), id_a, id_b),
                                        return_dtype=pl.Boolean)

def contains(candidate_id):
    """
    Returns a logical expression for polars dataframe to specify rows where
    column "Votes" is a list that contains candidate_id
    """
    return pl.col("Votes").list.contains(candidate_id)

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
    #mask = (
        #(pl.col("Votes").list.get(0) == 525) & 
        #(pl.col("Votes").list.get(1, null_on_oob=True) == 527) & 
        #(pl.col("Votes").list.get(2, null_on_oob=True) == 527) & 
        #(pl.col("Votes").list.get(3, null_on_oob=True) == 45)
        #)
            
    #round_votes = ballot_counts.
    print("First to second choise breakdowns:")
    for round1_cand_id in candidates:
        first_cand = (exact_round(round1_cand_id,0))
        first_cand_votes = ballot_counts.filter(first_cand)["count"].sum()
        only_cand = (bullet(round1_cand_id))
        only_cand_votes = ballot_counts.filter(only_cand)["count"].sum()
        print(candidates[round1_cand_id], "-", 
              first_cand_votes, "votes")
        for round2_cand_id in candidates:
            if round2_cand_id == round1_cand_id:
                print("  ", candidates[round1_cand_id], "-",
                      only_cand_votes, "votes -",
                      "{:.3f} %".format(100*only_cand_votes/first_cand_votes))
                continue
            next_cand = first_cand & (exact_round(round2_cand_id,1))
            next_cand_votes = ballot_counts.filter(next_cand)["count"].sum()
            print("  ", candidates[round2_cand_id], "-",
                  next_cand_votes, "votes -",
                  "{:.3f} %".format(100*next_cand_votes/first_cand_votes))
    
    ballot_counts = ballot_counts.with_columns(
        pl.col("Votes").list.eval(
            pl.element().filter(pl.element().is_in(list(candidates)))
            )
        .list.first() # Gets the highest ranked active candidate, or null if empty
        .alias("top_choice"))
    top_counts = (ballot_counts.filter(
        pl.col("top_choice").is_not_null())# Exclude exhausted ballots
        .group_by("top_choice")
        .agg(pl.col("count").sum())
        .sort("count", descending=True))
    print()
    print("Relative Preferences for voters who rank:")
    try:
        third_before_2_before_1 = (ranked_ahead(top_counts["top_choice"][2], 
                                                top_counts["top_choice"][1]) &
                                   ranked_ahead(top_counts["top_choice"][1], 
                                                top_counts["top_choice"][0]))
    except IndexError as e:
        print("Fewer than three valid candidates. Can't do this calculation")
        raise e
    third_before_1_before_2 = (ranked_ahead(top_counts["top_choice"][2], 
                                            top_counts["top_choice"][0]) &
                               ranked_ahead(top_counts["top_choice"][0], 
                                            top_counts["top_choice"][1]))
    three_2_1_votes = ballot_counts.filter(third_before_2_before_1)["count"].sum()
    three_1_2_votes = ballot_counts.filter(third_before_1_before_2)["count"].sum()
    print(three_2_1_votes, "voters rank", 
          candidates[top_counts["top_choice"][2]], "then",
          candidates[top_counts["top_choice"][1]], "ahead of",
          candidates[top_counts["top_choice"][0]])
    print(three_1_2_votes, "voters rank", 
          candidates[top_counts["top_choice"][2]], "then",
          candidates[top_counts["top_choice"][0]], "ahead of",
          candidates[top_counts["top_choice"][1]])
    print()
    try:
        fourth_before_2_before_1 = (ranked_ahead(top_counts["top_choice"][3], 
                                                 top_counts["top_choice"][1]) &
                                    ranked_ahead(top_counts["top_choice"][1], 
                                                 top_counts["top_choice"][0]))
    except IndexError as e:
        print("Fewer than three valid candidates. Can't do this calculation")
        raise e
    fourth_before_1_before_2 = (ranked_ahead(top_counts["top_choice"][3], 
                                             top_counts["top_choice"][0]) &
                                ranked_ahead(top_counts["top_choice"][0], 
                                             top_counts["top_choice"][1]))
    four_2_1_votes = ballot_counts.filter(fourth_before_2_before_1)["count"].sum()
    four_1_2_votes = ballot_counts.filter(fourth_before_1_before_2)["count"].sum()
    print(four_2_1_votes, "voters rank", 
          candidates[top_counts["top_choice"][3]], "then",
          candidates[top_counts["top_choice"][1]], "ahead of",
          candidates[top_counts["top_choice"][0]])
    print(four_1_2_votes, "voters rank", 
          candidates[top_counts["top_choice"][3]], "then",
          candidates[top_counts["top_choice"][0]], "ahead of",
          candidates[top_counts["top_choice"][1]])
                                                                  
    with pl.Config(tbl_rows=-1, tbl_cols=-1, tbl_width_chars=-1):
        print(ballot_counts)
        #print(ballot_counts.filter(mask))