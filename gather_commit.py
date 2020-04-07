from git import Repo, Diff, Commit, Actor
import os
import datetime
import time
import json
import shutil


def debug(*messages):
    import inspect
    caller = inspect.stack()[1]
    fpath = caller.filename
    ln = caller.lineno
    location = "File \"%s\", line %d " % (fpath, ln) + '\t'
    message = ' '.join([str(m) for m in messages])
    t = time.strftime('%y-%m-%d %H:%M:%S')
    print(location + t + '\t' + message)


def download_commit_summaries(
        repo_owner_name, repo_name, time_budget,
        include_merge_commit=False, max_commits=100000,
        delete_repo_after_finish=True):
    if not os.path.exists('tmp_repo'):
        os.mkdir('tmp_repo')
    if not os.path.exists('commit_data'):
        os.mkdir('commit_data')
    debug(
        'Generating Summary for \"' + repo_owner_name + '/' + repo_name + '\"',
        ' in last ', time_budget, 'months'
    )
    if not include_merge_commit:
        debug('Ignoring the merge commits!')
    else:
        debug('Including the merge commits!')
    repository_path = 'tmp_repo/' + repo_name
    if not os.path.exists(repository_path):
        debug('Cloning Repository from', 'https://github.com/' + repo_owner_name + '/' + repo_name + '.git',
              'into', repository_path)
        repo = Repo.clone_from(
            'https://github.com/' + repo_owner_name + '/' + repo_name + '.git', repository_path)
    else:
        repo = Repo(repository_path)
    author_str_to_id = {}
    file_str_to_id = {}
    all_authors = []
    all_files = []
    all_commit_summaries = []
    time_margin = (datetime.datetime.now() - datetime.timedelta(time_budget * 365 / 12)) \
        if time_budget != 1 else None
    if time_margin is not None:
        timestamp_margin = time_margin.timestamp()
    commits = list(repo.iter_commits('master'))
    debug('Total commits', len(commits))
    for i, commit in enumerate(commits):
        mx = int(min(max_commits, len(commits)) / 100)
        if i % mx == 0:
            debug("Completed", i / mx, "%")
        if i == max_commits:
            break
        author_time = commit.authored_datetime
        if time_margin is not None and author_time.timestamp() < timestamp_margin:
            break
        author = commit.author
        commit_time = commit.committed_datetime
        if author_time == commit_time:
            post_commit_change = False
        else:
            post_commit_change = True
        file_ids = []
        if not include_merge_commit and len(commit.parents) > 1:
            continue
        for parent in commit.parents:
            diffs = commit.diff(parent)
            for diff in diffs:
                fp = diff.b_path.strip()
                if fp not in file_str_to_id.keys():
                    file_str_to_id[fp] = len(file_str_to_id.keys())
                    new_file = {
                        'id': file_str_to_id[fp],
                        'file_path': fp
                    }
                    all_files.append(new_file)
                file_ids.append(file_str_to_id[fp])
        author_str = author.name + '-' + author.email
        if author_str not in author_str_to_id:
            author_str_to_id[author_str] = len(author_str_to_id)
            author_dict = {
                'id': author_str_to_id[author_str],
                'name': author.name,
                'email': author.email
            }
            all_authors.append(author_dict)
        commit_summary = {
            'id': commit.hexsha,
            'author_id': author_str_to_id[author_str],
            'timestamp': author_time.timestamp(),
            'time': str(author_time),
            'files': file_ids,
            'post_commit_change': post_commit_change,
            'is_merge_commit': len(commit.parents) > 1
        }
        all_commit_summaries.append(commit_summary)

    save_dir = 'commit_data/' + repo_owner_name + '_' + repo_name
    if not os.path.exists(save_dir):
        os.mkdir(save_dir)
    author_file = open(os.path.join(save_dir, 'authors.json'), 'w')
    json.dump(all_authors, author_file)
    author_file.close()

    file_path_file = open(os.path.join(save_dir, 'files.json'), 'w')
    json.dump(all_files, file_path_file)
    file_path_file.close()

    commits_file = open(os.path.join(save_dir, 'commits.json'), 'w')
    json.dump(all_commit_summaries, commits_file)
    commits_file.close()
    if delete_repo_after_finish:
        shutil.rmtree(repository_path)
    debug('Total authors: %d\tTotal Unique files: %d\tTotal commits: %d' \
          % (len(all_authors), len(all_files), len(all_commit_summaries)))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--owner', help='Repository owner username', required=True, type=str)
    parser.add_argument('--repo', help='Name of the Repository', required=True, type=str)
    parser.add_argument(
        '--time_back', help='History budget backwards in time (in month)', type=int, default=12)
    parser.add_argument('--delete_repo', help='Delete repository after use', action='store_true')
    parser.add_argument('--include_merge', help='Include Merge Changes', action='store_true')
    parser.add_argument('--max_commits', help='Number of max commits', type=int, default=1000000)
    args = parser.parse_args()
    download_commit_summaries(
        repo_owner_name=args.owner,
        repo_name=args.repo,
        time_budget=args.time_back,
        include_merge_commit=args.include_merge,
        delete_repo_after_finish=args.delete_repo,
        max_commits=args.max_commits
    )