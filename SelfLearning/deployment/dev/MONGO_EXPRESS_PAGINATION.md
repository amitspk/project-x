# MongoDB Express - Viewing All Documents

## Why Not All Documents Show at Once

MongoDB Express uses **pagination by default** for performance reasons. When viewing a collection, it shows a limited number of documents per page (typically 50-100 documents).

## How to View All Documents

### Option 1: Use Pagination Controls in the UI

1. **Navigate through pages**: Use the "Next" and "Previous" buttons at the bottom of the document list
2. **Increase documents per page**: Look for a dropdown or input field that allows you to select how many documents to show per page (e.g., 50, 100, 200, 500)

### Option 2: Use MongoDB Query/Filter

If you need to see specific documents:
1. Click on the collection name
2. Use the query/filter box to search for specific documents
3. You can use MongoDB query syntax (e.g., `{"status": "completed"}`)

### Option 3: Export Data

1. Click on the collection
2. Look for an "Export" or "Download" option to get all documents in JSON format

### Option 4: Use MongoDB Shell/Compass

For viewing all documents without pagination limits:
- **MongoDB Compass**: Download and connect to `mongodb://admin:password@localhost:27017/blog_qa_db?authSource=admin`
- **MongoDB Shell**:
  ```bash
  docker exec -it fyi-widget-mongodb mongosh -u admin -p password --authenticationDatabase admin
  use blog_qa_db
  db.your_collection.find().pretty()
  ```

## Checking Total Document Count

In MongoDB Express:
1. Click on the collection name
2. Look at the collection stats/header - it should show the total count of documents in the collection

## Notes

- Pagination is **expected behavior** - it's designed to handle large collections efficiently
- Default pagination limit is usually **50-100 documents per page**
- There's no environment variable to disable pagination in mongo-express
- The UI controls allow you to adjust how many documents are shown per page

