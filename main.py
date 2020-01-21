import os
import threading
import json

from classes.worker import Worker


def main():
    print('hotwheel bot running')

    # define lock for the account file
    lock = threading.Lock()

    # load settings from json
    print('loading settings from settings.json')
    try:
        with open(os.path.abspath('settings.json')) as settings_file:
            try:
                settings = json.load(settings_file)
            except json.decoder.JSONDecodeError:
                print('error parsing json in settings')
                exit(-1)
    except IOError:
        print('error loading settings from file')
        exit(-1)

    if settings['use_catchall'] and not settings['generate_accounts']:
        # load up a set of privacy cards to use for each catchall task
        print('loading privacy cards from cards.json')
        try:
            with open(os.path.abspath('cards.json')) as cards_file:
                try:
                    cards_json = json.load(cards_file)
                except json.decoder.JSONDecodeError:
                    print('error parsing json in cards')
                    exit(-1)
        except IOError:
            print('error opening cards.json')
            exit(-1)

        # if we have the use catchall flag, then we read from 'accounts.txt' (instead of tasks json)
        # the file is generated using the 'generate_accounts' flag
        # {EMAIL}:{PASSWORD}:{FIRST_NAME}:{LAST_NAME}
        print('loading tasks from accounts.txt')
        try:
            with open(os.path.abspath('accounts.txt'))as accounts_file:
                # if the file gets really big, this could blow up since it reads right into memory
                account_lines = accounts_file.readlines(16000)
                # remove whitespace chars
                account_lines = list(map(lambda x: x.strip(), account_lines))
                # remove '' strings
                account_lines = list(filter(None, account_lines))
                tasks = dict()
                tasks['tasks'] = list()
                for idx, account_line in enumerate(account_lines):
                    split_account_line = account_line.split(':')
                    # use card index in case the list of accounts exceeds list of cards
                    card_index = idx
                    if card_index >= len(cards_json['cards']):
                        card_index = 0
                    try:
                        tasks['tasks'].append({
                            'email': split_account_line[0],
                            'password': split_account_line[1],
                            'first_name': split_account_line[2],
                            'last_name': split_account_line[3],
                            'cc_num': cards_json['cards'][card_index]['cc_num'],
                            'cc_exp_m': cards_json['cards'][card_index]['cc_exp_m'],
                            'cc_exp_y': cards_json['cards'][card_index]['cc_exp_y'],
                            'cc_cvv': cards_json['cards'][card_index]['cc_cvv'],
                            'cc_brand': cards_json['cards'][card_index]['cc_brand']
                        })
                    except IndexError:
                        print('error missing data from account line')
                        exit(-1)
                    except KeyError:
                        print('error missing data from card json')
                        exit(-1)
        except IOError:
            print('error loading tasks from file')
            exit(-1)
    else:
        print('loading tasks from tasks.json')
        try:
            with open(os.path.abspath('tasks.json')) as tasks_file:
                try:
                    tasks = json.load(tasks_file)
                except json.decoder.JSONDecodeError:
                    print('error parsing json in tasks')
        except IOError:
            print('error loading tasks from file')
            exit(-1)

    if not settings['generate_accounts'] and settings['use_catchall'] and len(tasks) < settings['catchall_num_tasks']:
        print('error not enough tasks for catchall setting')
        print('have {} tasks and catchall set for {}'.format(len(tasks), settings['catchall_num_tasks']))
        exit(-1)

    threads = list()
    if settings['generate_accounts']:
        for idx in range(settings['generate_accounts_num_tasks']):
            print('starting generate task {}'.format(idx))
            w = Worker(
                settings=settings,
                task=None,
                account_lock=lock
            )
            threads.append(w)
            threads[idx].start()
    elif settings['use_catchall']:
        for idx in range(settings['catchall_num_tasks']):
            print('starting catchall task {}'.format(idx))
            w = Worker(
                settings=settings,
                task=tasks['tasks'][idx],
                account_lock=lock
            )
            threads.append(w)
            threads[idx].start()
    else:
        for idx, task in enumerate(tasks['tasks']):
            print('starting task {}'.format(idx))
            w = Worker(
                settings=settings,
                task=task,
                account_lock=lock
            )
            threads.append(w)
            threads[idx].start()


if __name__ == '__main__':
    main()
