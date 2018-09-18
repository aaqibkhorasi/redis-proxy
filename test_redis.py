from flask import Flask, render_template, request
from redis import StrictRedis
from werkzeug.contrib.cache import SimpleCache
from redisProxy import redis_db,cache, CACHE_KEYS, CACHE_STORE
import redisProxy

import time
import json
import unittest
import requests
import logging
import os

DB_HOST = os.environ.get("DB_HOST", "redis://cache")
DB_PORT = os.environ.get("DB_PORT", 6379)
MAX_CONNECTION = redisProxy.MAX_CONNECTION
CACHE_SIZE = os.environ.get("CACHE_SIZE")
POP_SIZE = redisProxy.POP_SIZE
LOCAL_EXPIRE = redisProxy.LOCAL_EXPIRE         # minutes
CACHE_KEYS = "LRU-KEYS"    # Used as a purpose to hold ranks of each keys
CACHE_STORE = "LRU-STORE"  # Used to store key-value pair
cache = redisProxy.cache

redis_db = StrictRedis(
    host=DB_HOST,
    port=DB_PORT,
)


class TestRedis(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestRedis, self).__init__(*args, **kwargs)

    def setUp(self):
        print("hey in setUp")
        redis_db.flushdb()
        
    def test_post(self):
        """
        Test to check if post request is completed succesfully
        """
        logging.info("Running Test Case #1: \nTest to check if "
                     "request is completed succesfully")
        post_request = requests.post('http://app:5000/hello', json={'value': 'world'})
        returned_value = post_request.json()
        expected_value = json.dumps({"hello": "success"})
        self.assertEqual(json.dumps(returned_value), expected_value)
        redis_db.flushall()
        post_request = requests.get('http://app:5000/clear/hello')

    def test_get_none_key(self):
        """
        Test to check if invalid key is given returns key not found
        """
        logging.info("Running Test Case #2: \nTest to check if invalid key is given returns key not found")
        get_request = requests.get('http://app:5000/invalid_key')
        returned_value = get_request.json()
        expected_value = json.dumps({'Error': 'Key not found'})
        self.assertEqual(json.dumps(returned_value), expected_value)
        redis_db.info()
        redis_db.flushall()

    def test_get_valid_key(self):
        """
        Test to check if valid key is given returns value
        """
        logging.info("Running Test Case #3: \nTest to check if valid key is given returns value")
        headers = {'Content-type': 'application/json'}
        post = requests.post('http://app:5000/hello', data=json.dumps({"value": "world"}), headers=headers)
        print(post.json())
        time.sleep(2)
        get_request = requests.get('http://app:5000/hello')
        print(get_request.json())
        returned_value = get_request.json()
        expected_value = json.dumps({"key": "hello", "value": "world"})
        self.assertEqual(json.dumps(returned_value), expected_value)
        redis_db.flushall()

    def test_get_valid_key_local_cache(self):
        """
        Test to check if get request gets value from local cache instead of REDIS
        Redis ZSCORE Should be same before request
        """
        logging.info("Running Test Case #4 : \nTest to check if get request gets"
                     " value from local cache instead of REDIS. \nRedis ZSCORE Should be same before request")
        requests.get('http://app:5000/clear/hello5')
        post_request = requests.post('http://app:5000/hello5', json={'value': 'world'})
        time.sleep(2)
        get_request = requests.get('http://app:5000/hello5')  # Reads from Redis Instance
        get_request = requests.get('http://app:5000/hello5')  # Reads from from local cache
        key_rank = redis_db.zscore(CACHE_KEYS, "hello5")
        self.assertEqual(1.0, key_rank)   # Reads from
        requests.get('http://app:5000/clear/hello5')
        redis_db.flushall()

    def test_get_valid_key_local_cache_expired(self):
        """
        Test to check if local cache value expires after SPECIFIED time
        """
        logging.info("Running Test Case #5: \nTest to check if local cache"
                     " value expires after SPECIFIED time")
        post_request = requests.post('http://app:5000/hello10', json={'value': 'world'})
        clear_request = requests.get('http://app:5000/clear/hello10')
        get_request = requests.get('http://app:5000/hello10')  # Reads from Redis Instance
        key_rank = redis_db.zscore(CACHE_KEYS, "hello10")
        self.assertNotEqual(0.0, key_rank)  # Reads from
        clear_request = requests.get('http://app:5000/clear/hello10')


    def test_get_valid_key_redis_cache(self):
        """
        Test to check if get request gets value from redis cache instead of local cache
        Redis ZSCORE should change after request
        """
        logging.info("Running Test Case #6: \nTest to check if request "
                     "gets value from redis cache")
        headers = {'Content-type': 'application/json'}
        post_request = requests.post('http://app:5000/hello', data=json.dumps({"value": "world"}), headers=headers)
        time.sleep(1)
        clear_request = requests.get('http://app:5000/clear/hello')
        get_request = requests.get('http://app:5000/hello')  # Reads from Redis Instance
        time.sleep(1)
        keys = redis_db.zrange(CACHE_KEYS, 0, CACHE_SIZE)
        key_rank = redis_db.zscore(CACHE_KEYS, "hello")
        self.assertEqual(1.0, key_rank)  # Reads from

    def test_get_valid_key_redis_cache_capacity_reached(self):
        """
        Test to check if redis cache LRU-STORE and LRU-KEYS is updated and
        LRU is used to evict a key with less zscore
        """
        logging.info("Running Test Case #7: \nest to check if redis cache LRU-STORE and"
                     " LRU-KEYS is updated and \n LRU is used to evict a key with less zscore")
        headers = {'Content-type': 'application/json'}

        redis_db.flushall()
        clear_request = requests.get('http://app:5000/clear/hello')
        clear_request = requests.get('http://app:5000/clear/hello2')

        post_request = requests.post('http://app:5000/hello', data=json.dumps({"value": "world"}), headers=headers)
        time.sleep(2)
        post_request = requests.post('http://app:5000/hello2', data=json.dumps({"value": "world2"}), headers=headers)
        time.sleep(2)

        # Maximum Capacity has reached here
        get_request = requests.get('http://app:5000/hello')  # Reads from Redis Instance
        key_rank = redis_db.zscore(CACHE_KEYS, "hello")   # 1.0
        key_rank2 = redis_db.zscore(CACHE_KEYS, "hello2")  # 0.0

        post_request = requests.post('http://app:5000/hello3', json={'value': 'world'})
        time.sleep(2)
        current_range = redis_db.zrange(CACHE_KEYS, 0, CACHE_SIZE)
        current_keys = redis_db.hkeys(CACHE_STORE)

        self.assertEqual([b'hello', b'hello3'], current_keys)
        self.assertEqual(int(CACHE_SIZE), redis_db.zcard(CACHE_KEYS))
        redis_db.flushall()
        clear_request = requests.get('http://app:5000/clear/hello')
        clear_request = requests.get('http://app:5000/clear/hello2')

    def tearDown(self):
        redis_db.flushdb()

if __name__ == '__main__':
    unittest.main()
