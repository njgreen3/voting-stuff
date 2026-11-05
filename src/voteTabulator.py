import json
import os
import glob

def clean_ballot(marks):
    """
    Cleans a single ballot according to Alaska's RCV rules.
    marks: list of dicts with 'Rank' and 'CandidateId'
    """
    # Sort marks by rank order
    marks.sort(key=lambda x: x['Rank'])
    
    valid_ballot = []
    last_rank = 0
    seen_candidates = set()
    
    # Identify overvoted ranks (multiple candidates given the same rank)
    rank_counts = {}
    for mark in marks:
        rank = mark['Rank']
        rank_counts[rank] = rank_counts.get(rank, 0) + 1
        
    for mark in marks:
        rank = mark['Rank']
        candidate = mark['CandidateId']
        
        # Rule: Overvote invalidates this rank and all subsequent rankings
        if rank_counts[rank] > 1:
            break
            
        # Rule: Skipping two or more consecutive rankings invalidates subsequent rankings
        # (e.g., jumping from Rank 1 to Rank 4 means a difference of 3. A difference >= 3 is invalid)
        if rank - last_rank >= 3:
            break
            
        # Rule: A candidate can only be counted once per ballot
        if candidate not in seen_candidates:
            valid_ballot.append(candidate)
            seen_candidates.add(candidate)
            
        last_rank = rank
        
    return valid_ballot


def parse_cvr_json(file_path, target_contest_id, ballots=[]):
    """
    Parses a Dominion CVR_Export.json file to extract cleaned RCV ballots.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    
    # Navigate the Dominion JSON schema structure
    sessions = data.get('Sessions', [])
    for session in sessions:
        original = session.get('Original', {})
        cards = original.get('Cards', [])
        
        for card in cards:
            contests = card.get('Contests', [])
            
            for contest in contests:
                if contest.get('Id') == target_contest_id:
                    # Extract active marks for this contest
                    marks = [
                        m for m in contest.get('Marks', [])
                        if m.get('IsVote', False)
                    ]
                    
                    if marks:
                        cleaned = clean_ballot(marks)
                        if cleaned:
                            ballots.append(cleaned)
                            
    return ballots

def parse_candidate_json(file_path, target_contest_id):
    """
    Parses a Dominion CandidateManifest.json file. Only selects candates in 
    target_contest_id
    Makes a dictionary with candidate ids as keys and names as values
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    candidates = {}
    
    # Navigate the Dominion JSON schema structure
    lists = data.get('List', [])
    for candidate in lists:
        if candidate.get('ContestId') == target_contest_id:
            candidateID = candidate.get("Id")
            candidateName = candidate.get("Description")
            candidates[candidateID] = candidateName
    return candidates

def tabulate_rcv(ballots, candidateNames={}):
    """
    Tabulates the cleaned ballots round-by-round.
    """
    # Get all candidates who received at least one valid vote
    active_candidates = set(candidate for ballot in ballots for candidate in ballot)
    # If candidate names is empty, just fill with ids instead
    if not candidateNames:
        for candidateID in active_candidates:
            candidateNames[candidateID] = candidateID
    round_num = 1
    
    while True:
        print(f"\n{'-'*15} ROUND {round_num} {'-'*15}")
        
        tallies = {c: 0 for c in active_candidates}
        active_ballots_count = 0
        
        # Allocate ballots to the highest-ranked active candidate
        for ballot in ballots:
            for candidate in ballot:
                if candidate in active_candidates:
                    tallies[candidate] += 1
                    active_ballots_count += 1
                    break # Stop looking at this ballot once the active vote is placed
                    
        # Print standings for this round
        for candidate, votes in sorted(tallies.items(), key=lambda x: x[1], reverse=True):
            pct = (votes / active_ballots_count * 100) if active_ballots_count > 0 else 0
            print(f"Candidate {candidateNames[candidate]}: {votes} votes ({pct:.2f}%)")
            
        if not tallies:
            print("No active candidates remain.")
            break
            
        # Check if the leading candidate reached 50% + 1 of ACTIVE ballots
        highest_candidate, highest_votes = max(tallies.items(), key=lambda x: x[1])
        if highest_votes > (active_ballots_count / 2):
            print(f"\nWINNER DECLARED: Candidate {candidateNames[highest_candidate]} wins with {highest_votes} votes!")
            break
            
        # If only two candidates remain, the tabulation ends 
        if len(active_candidates) <= 2:
            print(f"\nTABULATION COMPLETE: Candidate {candidateNames[highest_candidate]} wins the final round.")
            break
            
        # Eliminate the candidate with the fewest votes
        # (In the event of a tie for last place, sorting by candidate ID acts as a deterministic tiebreaker. 
        #  Real elections resolve this via coin toss/drawing lots.)
        lowest_candidate, lowest_votes = min(tallies.items(), key=lambda x: (x[1], x[0]))
        
        print(f"\n> Eliminating Candidate {candidateNames[lowest_candidate]} ({lowest_votes} votes)")
        active_candidates.remove(lowest_candidate)
        
        round_num += 1


if __name__ == "__main__":
    # Example usage:
    data_path = os.path.join("..","data")
    cvr_files = glob.glob(os.path.join(data_path,"CvrExport*.json"))
    candidate_file = os.path.join(data_path,"CandidateManifest.json")
    
    # You will need to look at the JSON file to find the specific "Id" for the contest you want to tabulate.
    contest_id_to_tabulate = 6 
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
    tabulate_rcv(election_ballots, candidates)