import os
import json

from classes.worker import Worker


def main():
    print('hotwheel bot running')

    # load settings from json
    print('loading settings from settings.json')
    try:
        with open(os.path.abspath('settings.json')) as settings_file:
            try:
                settings = json.load(settings_file)
            except json.decoder.JSONDecodeError:
                print('error parsing json in settings')
    except IOError:
        print('error loading settings from file')
        exit(-1)

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

    threads = list()
    for idx, task in enumerate(tasks['tasks']):
        print('starting task {}'.format(idx))
        w = Worker(
            settings=settings,
            task=task
        )
        threads.append(w)
        threads[idx].start()


if __name__ == '__main__':
    main()
