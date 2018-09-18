from flask import Flask, render_template, request
from redis import StrictRedis
from werkzeug.contrib.cache import SimpleCache
from rq import Queue
from rq.job import Job
import time
from urllib.parse import urlparse

import os
import json

DB_HOST = "localhost"
DB_PORT = 6379
MAX_CONNECTION = 3
CACHE_SIZE = 2
POP_SIZE = 1
REDIS_EXPIRE = 1           # minutes
LOCAL_EXPIRE = 0.5          # minutes
CACHE_KEYS = "LRU-KEYS"    # Used as a purpose to hold ranks of each keys
CACHE_STORE = "LRU-STORE"  # Used to store key-value pair

app = Flask(__name__)


cache = SimpleCache()

redis_db = StrictRedis(
    host=DB_HOST,
    port=DB_PORT,
    decode_responses=True,
)
q = Queue(connection=redis_db)
pipeline_object = redis_db.pipeline()


def run():
    app.run(debug=True)


def set_item(key, value):
    """
    Add value to a given key in hash if it doesnt exist
    It will evict keys(POP_SIZE) if the capacity is full
    """
    if not redis_db.hexists(CACHE_STORE, key):  # Time complexity: O(1)
        make_space()
        redis_db.hset(CACHE_STORE, key, value)      # setting up key-value pair   O(1)
        #Time complexity: O(log(N)) for each item added, where N is the number of elements in the sorted set
        redis_db.zadd(CACHE_KEYS, 0, key)           # Init a key with 0 rank



def make_space():
    """
    Delete defined set of keys if hash has reached to its threshhold

    """
    if redis_db.zcard(CACHE_KEYS) >= CACHE_SIZE:  #O(1)
        #O(log(N)+M) with N being the number of elements in the sorted set and M the number of elements returned.
        to_pop = redis_db.zrange(CACHE_KEYS, 0, POP_SIZE-1)   # Give range of keys in sorted set


        #Time complexity: O(log(N)+M) with N being the number of elements in the sorted set and M the number of elements removed by the operation.
        # Removes first POP_SIZE elements in the sorted set with rank between [0-POPSIZE)
        redis_db.zremrangebyrank(CACHE_KEYS, 0, POP_SIZE-1)
        print ("removing value {0}".format(to_pop))

        print ("BEFORE, NOW SIZE {0}".format(redis_db.hlen(CACHE_STORE)))
        #Time complexity: O(N) where N is the number of fields to be removed.
        redis_db.hdel(CACHE_STORE, *to_pop)  # Remove specified fields, i.e to_pop   O(n)
        print ("DELETED, NOW SIZE {0}".format(redis_db.hlen(CACHE_STORE)))


def get_item(key):
    """
    Gets value of a given key and increase rank of that key by 1
    """
    # pipeline_object.watch(redis_db.hkeys())
    result = redis_db.hget(CACHE_STORE, key)  #O(1)
    if result: # Cache hit, means found
        #O(log(N)) where N is the number of elements in the sorted set.
        redis_db.zincrby(CACHE_KEYS, key, 1.0)  # Increment member for LRU for ranking purpose
    return result


def delete_local_cache_key(key):
    global cache
    cache.delete(key)


def index():
    results = {}
    if request.method == "POST":
        # get url that the person has entered
        url = request.form['url']
        if 'http://' not in url[:7]:
            url = 'http://' + url
        job = q.enqueue_call(
            func=proxy, args=(url), result_ttl=5000
        )
        print(job.get_id())

    return render_template('index.html', results=results)

@app.route('/<key>', methods=['GET', 'POST'])
def proxy(key):
    if request.method == "GET":
        local_value = cache.get(key)
        if local_value is not None:
            print('Coming from local')
            res = {'key': key, 'value': local_value}
            return json.dumps(res)

        value = get_item(key)
        if value is None:
            value = "No value set for the given key"
            res = {"Error": "Key not found"}
            return json.dumps(res)
        cache.set(key, value, timeout=LOCAL_EXPIRE*60)
        res = {'key': key, 'value': value}
        return json.dumps(res)

    job = q.enqueue_call(
        func=process_q, args=(key, request.data), result_ttl=5000
    )

    print(job.get_id())
    res = {'Message': 'Job Enqueued', 'Job ID': job.get_id()}

    return json.dumps(res)


def process_q(key, data):
    print(data)
    data_dict = json.loads(data)
    value = data_dict['value']
    print(data_dict['value'])
    set_item(key, value)
    res = {"key": key, "value": value}
    return "Good"


@app.route('/job/<job_id>', methods=['GET'])
def job_status(job_id):
    rq_job = Job(id=job_id, connection=redis_db)
    print(rq_job.get_status())
    print(rq_job)
    res = {'Job ID': job_id, 'Status': rq_job.get_status()}
    return json.dumps(res)

@app.route('/jobs', methods=['GET'])
def jobs():
    jobs = q.get_job_ids()
    print(jobs)
    #TODO
    return 'Send JSON'

@app.route('/clear/<key>', methods=['GET'])
def clear_cache(key):
    delete_local_cache_key(key)
    res = "{0} is cleared from local cache".format(key)
    return json.dumps(res)


@app.route('/', methods=['GET'])
def index():
    render_template('templates/home_page.html')


if __name__ == '__main__':
    cache.clear()
    app.run(host='0.0.0.0', debug=True)
