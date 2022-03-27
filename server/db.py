import json


class Database:
    def __init__(self, capacity: int = 100, db_path: str = 'nft_db.json'):
        self.capacity = capacity
        self.db_path = db_path
        try:
            with open(self.db_path) as f:
                self.data = json.load(f)
                print('Successfully restore database!')
        except:
            self.data = []

    def _clip(self):
        self.data = self.data[-self.capacity:]

    def insert(self, item):
        if len(self.data) > self.capacity * 2:
            self._clip()
        self.data.append(item)

    def query_all(self):
        return self.data

    def save(self):
        with open(self.db_path, 'w') as f:
            self._clip()
            json.dump(self.data, f)
