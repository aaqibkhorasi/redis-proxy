test:
	docker-compose -f docker-compose-test.yml up -d
	docker exec testContainer nosetests -v
	docker stop cache
	docker stop app
	docker stop worker
	docker stop testContainer

app:
	docker-compose up --build -d

stop:
	docker-compose down
