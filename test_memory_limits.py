import asyncio, csv, io, json, unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch
import main
from fastapi import Response, HTTPException

class MemoryTests(unittest.TestCase):
    def setUp(self):
        main.DATASETS.clear()
        main.PENDING_DATASETS.clear()

    def create(self, n=1):
        return main.create_dataset(main.DatasetRequest(start_date='2025-01-01', end_date='2025-01-02', num_records=n), Response())

    def test_concurrent_reservations(self):
        entered, finish = Event(), Event()
        original = main.generate_purchases
        def slow(**kwargs):
            entered.set()
            self.assertTrue(finish.wait(5))
            return original(**kwargs)
        with patch.object(main, 'MAX_TOTAL_RECORDS', 3), patch.object(main, 'generate_purchases', slow), ThreadPoolExecutor() as pool:
            pending = pool.submit(self.create, 3)
            try:
                self.assertTrue(entered.wait(5))
                with self.assertRaises(HTTPException) as caught:
                    self.create(1)
                self.assertEqual(caught.exception.status_code, 503)
            finally:
                finish.set()
            pending.result()
        self.assertFalse(main.PENDING_DATASETS)

    def test_failure_and_delete_release_capacity(self):
        with patch.object(main, 'generate_purchases', side_effect=RuntimeError('failed')):
            with self.assertRaises(RuntimeError): self.create()
        self.assertFalse(main.PENDING_DATASETS)
        with patch.object(main, 'MAX_DATASETS', 1):
            first = self.create()['dataset']['dataset_id']
            with self.assertRaises(HTTPException): self.create()
            main.delete_dataset(first, Response())
            self.create()

    def test_chunked_exports(self):
        rows = [{'id': i, 'text': 'hello, "world"\nUnicode: \u03bb', 'missing': None} for i in range(205)]
        chunks = list(main.stream_json(rows))
        self.assertEqual(len(chunks), 5)
        self.assertEqual(json.loads(''.join(chunks)), rows)
        chunks = list(main.stream_csv(rows))
        self.assertEqual(len(chunks), 3)
        parsed = list(csv.DictReader(io.StringIO(''.join(chunks))))
        self.assertEqual(len(parsed), 205)
        self.assertEqual(parsed[-1]['text'], rows[-1]['text'])
        self.assertEqual(json.loads(''.join(main.stream_json([]))), [])

    def test_download_slots_release_on_disconnect(self):
        dataset_id = self.create()['dataset']['dataset_id']
        first = main.download_dataset(dataset_id, 'json')
        second = main.download_dataset(dataset_id, 'csv')
        with self.assertRaises(HTTPException) as caught:
            main.download_dataset(dataset_id, 'json')
        self.assertEqual(caught.exception.status_code, 503)
        async def disconnected(*args):
            raise asyncio.CancelledError()
        async def run(response):
            with patch.object(main.StreamingResponse, '__call__', disconnected):
                with self.assertRaises(asyncio.CancelledError):
                    await response({}, None, None)
        asyncio.run(run(first)); asyncio.run(run(second))
        with self.assertRaises(HTTPException): main.download_dataset('missing', 'json')
        self.assertTrue(main.DOWNLOAD_SLOTS.acquire(False))
        self.assertTrue(main.DOWNLOAD_SLOTS.acquire(False))
        main.DOWNLOAD_SLOTS.release(); main.DOWNLOAD_SLOTS.release()

if __name__ == '__main__': unittest.main()
