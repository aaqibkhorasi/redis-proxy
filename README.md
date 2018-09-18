REDIS PROXY Documentation

Tools used:

- Python
  * redis-py (redis client library)
  * rq (For queue) 
- Docker
- make


High Level Architecture:

The http interface is running on flask server and the redis is used as an in memory database for this.
The application is running 3 instances at a same time:
1) Redis Server (Image in Docker)
2) Main App Server (Logic Layer)
3) Worker Process (Queue all the Post request and run it sequentially)


A) Post Request
1 The http server is connected to redis, so when ever new post request is fired on the server, the worker process will queue it and the job will be initiated.
  Each job will only run after previous job is completed. Job will store that data into the redis database.

    A.1 Case Maximum Capacity Reached:
    1) If the set threshold of redis keys is reached to its maximum, it will use LRU.
    2) Basically Least recent used key will be poped out of the redis backend.
    3) It uses the concept of ranking mechanism to sort and pop the least ranked key.
    4) In case of same rank keys, it will pop out the oldest key which has old age in the db.

B) Get Request Case:
1 Whenever the get request is done on the server, first time it will get the value from the server and save it to local cache memory. It increase the rank of that key in the backend.
2) Next time, depending if local cache is expired or not, it will fetch the value from local cache. If local cache is expired, it will jump to step 1).

Note: GET requests are not queued here. It can be queued in a same way if needed.


What does this code support:
1) Single Redis backend db, defaults to db0
2) Cached Get, .ie if request is fetched from db, it will store it into local cache with expiry time to avoid hitting db again.
3) Global Expiry: It will delete the proxy cache if the configured expiry time has passed.
4) LRU Eviction: If the keys has reached to its Configured maximum size it will pop out a least recently used key.
5) Cache Fixed Size : It will always retained configured fixed size keys
6) Set keys, Get keys
7) Queue Process to run post requests sequentially.


Algorithemic Complexity :

Post Request

set_item()
(O(log(N)+M) + O(log(N)+M) + O(n) ) + O(log(n)

make_space()
O(log(N)+M) + O(log(N)+M) + O(n)

Total : (O(log(N)+M) + O(log(N)+M) + O(n) ) + O(log(n)

Get Request:

get_item()
O(log(n)

Total : O(log(n)

Instructions on how to Run:

- `make test` To spin up the application stack, run the tests, stops application stack
- `make app` Spin up application stack
- `make stop` Stop the application stack
- `make clean` clean all the docker containers


Time Spent:

Total time = ~5-6 hours

Requirement Analysis (Understanding Project, Finding best available frameworks, etc): ~1hr

Setting up Redis, Cached Get, Global Expiry: ~45mins
lru eviction : ~1hr

Sequential Concurrent Processing + Testing: ~45mins

Manual + Unit Tests + System Test : 1hr
Docker Image : ~ 1.5hr 



Feature that's not included:

- No update key on existing key:

Since this is basic http interface, I didn't find it necessary to include that based on following reasons:
1) user will have to delete key and then add the new key value. This app doesn't have delete feature.
2) don’t want to overwrite a value that already exist by mistake
3) If updated key is inserted again, it take that value as a new key and reorder it. If the key is same and cache has reached to threshold then it will delete the old and new value both.
   For eg
    MAXIMUM_CACHE_SIZE = 2
    Current keys : [hello, hello2]
    RANK: [1, 0]
    After update on hello2, it will delete the key hello2 as this is ranked lowest.
    End Result : [hello]

4) To avoid hitting redis db and make use of local cache and expiry time to its fullest.
 If a key is updated and next time it make get request, it will take value(old value) from local cache instead of redis and that will wait until local cache will expire.


- No support of Redis Expiring

- already have LRU rule so doesn’t make sense to expire as it is main backend database
- It already supports LRU feature, so it will pop a key if it reaches its max capacity
