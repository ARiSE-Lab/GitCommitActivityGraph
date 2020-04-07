import argparse
import json
import os
from datetime import datetime
from datetime import timedelta

from gather_commit import debug


def sort_commits(all_commits):
    return sorted(all_commits,
                  key=lambda x: datetime.fromtimestamp(x['timestamp']))


def read_data(data_dir):
    author_file = open(os.path.join(data_dir, 'authors.json'))
    paths_file = open(os.path.join(data_dir, 'files.json'))
    commits_file = open(os.path.join(data_dir, 'commits.json'))
    return json.load(author_file), \
           json.load(paths_file), \
           sort_commits(json.load(commits_file))


def divide_commits_into_days(all_commits):
    day_to_commit = {}
    for commit in all_commits:
        t = datetime.fromtimestamp(commit['timestamp'])
        d = t.date()
        if d not in day_to_commit.keys():
            day_to_commit[d] = []
        day_to_commit[d].append(commit)
    return day_to_commit


def divide_into_interaction_chunks(all_commits, window_size=7, stride=1):
    daily_commits = divide_commits_into_days(all_commits)
    days = sorted(list(daily_commits.keys()))
    first_day = days[0]
    last_day = days[-1]
    day_chunks = []
    while first_day < last_day:
        next_day = first_day + timedelta(days=window_size-1)
        commits_in_this_chunk = []
        for day in daily_commits.keys():
            if first_day <= day <= next_day:
                commits_in_this_chunk.extend(daily_commits[day])
        window_chunk = {
            'first_day': first_day,
            'last_day': next_day,
            'commits': commits_in_this_chunk
        }
        first_day = first_day + timedelta(days=stride-1)
        day_chunks.append(window_chunk)
    return day_chunks


def create_author_interaction_graph(authors, commits):
    _author_interaction_graph = dict()
    for a in authors:
        _author_interaction_graph[a['id']] = set()
    modified_files = dict()
    for c in commits:
        for f in c['files']:
            if f not in modified_files:
                modified_files[f] = set()
            modified_files[f].add(c['author_id'])
    for f in modified_files:
        interacted_authors = modified_files[f]
        for a1 in interacted_authors:
            for a2 in interacted_authors:
                if a1 != a2:
                    _author_interaction_graph[a1].add(a2)
                    _author_interaction_graph[a2].add(a1)
    for a in _author_interaction_graph:
        _author_interaction_graph[a] = list(_author_interaction_graph[a])
    return _author_interaction_graph


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', help='Data Directory', type=str, required=True)
    parser.add_argument('--sliding_window_size',
                        help='Number of days to consider interaction', type=int,
                        default=7)
    parser.add_argument('--overlap_windows',
                        help='Overlap the windows', action='store_true')
    parser.add_argument('--stride',
                        help='Stride between windows', type=int, default=1)
    parser.add_argument('--save',
                        help='Path for saving result',
                        default='code_author_interaction_graphs')
    parser.add_argument(
        '--name', help='Name of this experiment', default=None)
    args = parser.parse_args()
    authors, files, commits = read_data(args.data)
    stride = args.stride
    stride += args.sliding_window_size if not args.overlap_windows else 0
    interaction_chunks = divide_into_interaction_chunks(
        all_commits=commits,
        window_size=args.sliding_window_size,
        stride=stride)
    all_interaction_graphs = [
        {
            'first_day': str(chunk['first_day']),
            'last_day': str(chunk['last_day']),
            'code_author_interaction': create_author_interaction_graph(
                authors, chunk['commits']
            )
        } for chunk in interaction_chunks
    ]
    exp_name = args.name
    if exp_name is None:
        exp_name = args.data.split('/')[-1].strip() \
            if '/' in args.data else args.data.strip()
    save_file_dir = args.save
    if not os.path.exists(save_file_dir):
        os.mkdir(save_file_dir)
    save_file_dir = os.path.join(save_file_dir, exp_name)
    if not os.path.exists(save_file_dir):
        os.mkdir(save_file_dir)
    file_name = ('code_author_inter-(window_size-' + str(args.sliding_window_size) + ')')
    file_name += '-'
    file_name += 'overlap' if args.overlap_windows else 'no_overlap'
    save_file = open(os.path.join(save_file_dir, file_name + '.json'), 'w')
    json.dump(all_interaction_graphs, save_file)
    save_file.close()
    pass
