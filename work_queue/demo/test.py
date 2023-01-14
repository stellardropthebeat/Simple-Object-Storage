import time
from celery.result import AsyncResult
from tasks import celery_app


def issue_tasks():
    tasks_1 = []
    tasks_2 = []
    for i in range(5):
        task = celery_app.send_task('tasks.add', queue='q01', kwargs={'x': i, 'y': i})
        tasks_1.append(task.task_id)
        task = celery_app.send_task('tasks.add', queue='q02', kwargs={'x': i * i, 'y': i * i})
        tasks_2.append(task.task_id)
    return tasks_1, tasks_2


def get_results(task_id):
    task_result = AsyncResult(task_id)
    result = {
        'task_id': task_id,
        'task_status': task_result.status,
        'task_result': task_result.result
    }
    return result


def run_task():
    tasks_1, tasks_2 = issue_tasks()
    while 1:
        done = True
        for tid in tasks_1:
            res = get_results(tid)
            if res['task_status'] == 'SUCCESS' or \
                    res['task_status'] == 'FAILURE':
                print(f'queue: q01, task: {tid}, result: {res["task_result"]}')
            else:
                done = False
                print(f'queue: q01, task: {tid}, status: {res["task_status"]}')
        for tid in tasks_2:
            res = get_results(tid)
            if res['task_status'] == 'SUCCESS' or \
                    res['task_status'] == 'FAILURE':
                print(f'queue: q02, task: {tid}, result: {res["task_result"]}')
            else:
                done = False
                print(f'queue: q02, task: {tid}, status: {res["task_status"]}')
        if done:
            print('\nAll tasks are finished.\n')
            break
        print('sleeping for 5 secound ...')
        time.sleep(5)


if __name__ == '__main__':
    run_task()

