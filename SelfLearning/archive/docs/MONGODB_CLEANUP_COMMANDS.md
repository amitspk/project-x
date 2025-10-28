# MongoDB Cleanup Commands Reference

This document provides comprehensive MongoDB cleanup commands for the SelfLearning project's `blog_ai_db` database.

## 🎯 **Quick Reference**

| Operation | Command Type | Risk Level | Use Case |
|-----------|--------------|------------|----------|
| Clear Data | `deleteMany({})` | ⚠️ Medium | Remove documents, keep structure |
| Drop Collections | `drop()` | 🚨 High | Remove everything including indexes |
| Drop Database | `dropDatabase()` | 💥 Critical | Nuclear option - removes all |

---

## 📊 **Data Cleanup Commands (Recommended)**

### **Clear All Collection Data**
```bash
# Clear all documents from all collections (keeps collections and indexes)
docker exec selflearning_mongodb mongosh -u admin -p password123 --authenticationDatabase admin blog_ai_db --eval "
// Show current document counts
print('📊 Before cleanup:');
db.getCollectionNames().forEach(function(collection) {
  const count = db[collection].countDocuments();
  print('  ' + collection + ':', count, 'documents');
});

// Clear all data
db.blog_summary.deleteMany({});
db.blog_qna.deleteMany({});
db.raw_blog_content.deleteMany({});
db.blog_meta_data.deleteMany({});
db.content_metadata.deleteMany({});
db.user_interactions.deleteMany({});
db.search_analytics.deleteMany({});
db.processing_jobs.deleteMany({});

// Show results
print('📊 After cleanup:');
db.getCollectionNames().forEach(function(collection) {
  const count = db[collection].countDocuments();
  print('  ' + collection + ':', count, 'documents');
});

print('✅ Data cleanup complete - collections preserved');
"
```

### **Clear Specific Collection Data**

#### **Clear Blog Content Only**
```bash
# Clear only blog-related data (summaries, questions, raw content)
docker exec selflearning_mongodb mongosh -u admin -p password123 --authenticationDatabase admin blog_ai_db --eval "
print('🗑️ Clearing blog content data...');
const summaryCount = db.blog_summary.countDocuments();
const qnaCount = db.blog_qna.countDocuments();
const rawCount = db.raw_blog_content.countDocuments();

db.blog_summary.deleteMany({});
db.blog_qna.deleteMany({});
db.raw_blog_content.deleteMany({});

print('✅ Cleared:', summaryCount, 'summaries,', qnaCount, 'Q&A,', rawCount, 'raw content');
"
```

#### **Clear Analytics Data Only**
```bash
# Clear only analytics and tracking data
docker exec selflearning_mongodb mongosh -u admin -p password123 --authenticationDatabase admin blog_ai_db --eval "
print('📈 Clearing analytics data...');
db.user_interactions.deleteMany({});
db.search_analytics.deleteMany({});
db.processing_jobs.deleteMany({});
print('✅ Analytics data cleared');
"
```

#### **Clear Vector Embeddings Only**
```bash
# Remove embedding fields from documents (keep other data)
docker exec selflearning_mongodb mongosh -u admin -p password123 --authenticationDatabase admin blog_ai_db --eval "
print('🔢 Removing embedding vectors...');
const result = db.blog_summary.updateMany(
  { embedding: { \$exists: true } },
  { 
    \$unset: { 
      embedding: '',
      embedding_model: '',
      embedding_provider: '',
      embedding_dimensions: '',
      embedding_generated_at: ''
    }
  }
);
print('✅ Removed embeddings from', result.modifiedCount, 'documents');
"
```

---

## 🗑️ **Collection Management Commands**

### **Drop Specific Collections**
```bash
# Drop individual collections (removes structure and data)
docker exec selflearning_mongodb mongosh -u admin -p password123 --authenticationDatabase admin blog_ai_db --eval "
print('🗑️ Dropping specific collections...');

// Check if collection exists before dropping
if (db.getCollectionNames().includes('blog_summary')) {
  db.blog_summary.drop();
  print('✅ Dropped blog_summary');
}

if (db.getCollectionNames().includes('blog_qna')) {
  db.blog_qna.drop();
  print('✅ Dropped blog_qna');
}

print('📊 Remaining collections:', db.getCollectionNames());
"
```

### **Drop All Collections (Dangerous)**
```bash
# ⚠️ WARNING: This removes all collections and their indexes
docker exec selflearning_mongodb mongosh -u admin -p password123 --authenticationDatabase admin blog_ai_db --eval "
print('🚨 WARNING: Dropping all collections...');
const collections = db.getCollectionNames();
print('📊 Found collections:', collections);

collections.forEach(function(collection) {
  if (!collection.startsWith('system.')) {
    const count = db[collection].countDocuments();
    print('🗑️ Dropping collection:', collection, '(', count, 'documents)');
    db[collection].drop();
  }
});

print('💥 All collections dropped!');
print('📊 Remaining collections:', db.getCollectionNames());
"
```

---

## 🔧 **Selective Data Cleanup**

### **Clear Data by Date Range**
```bash
# Clear old data (older than 30 days)
docker exec selflearning_mongodb mongosh -u admin -p password123 --authenticationDatabase admin blog_ai_db --eval "
const thirtyDaysAgo = new Date();
thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

print('🗓️ Clearing data older than:', thirtyDaysAgo);

const summaryResult = db.blog_summary.deleteMany({
  created_at: { \$lt: thirtyDaysAgo }
});

const qnaResult = db.blog_qna.deleteMany({
  created_at: { \$lt: thirtyDaysAgo }
});

print('✅ Removed', summaryResult.deletedCount, 'old summaries');
print('✅ Removed', qnaResult.deletedCount, 'old Q&A records');
"
```

### **Clear Data by Content ID**
```bash
# Clear specific blog content by ID
docker exec selflearning_mongodb mongosh -u admin -p password123 --authenticationDatabase admin blog_ai_db --eval "
const contentId = 'effective_use_of_threadlocal_in_java_app_5bbb34ce';

print('🎯 Clearing data for content ID:', contentId);

const summaryResult = db.blog_summary.deleteMany({ blog_id: contentId });
const qnaResult = db.blog_qna.deleteMany({ blog_id: contentId });
const rawResult = db.raw_blog_content.deleteMany({ blog_id: contentId });

print('✅ Removed:', summaryResult.deletedCount, 'summaries');
print('✅ Removed:', qnaResult.deletedCount, 'Q&A records');
print('✅ Removed:', rawResult.deletedCount, 'raw content');
"
```

### **Clear Failed Processing Jobs**
```bash
# Clear failed or stuck processing jobs
docker exec selflearning_mongodb mongosh -u admin -p password123 --authenticationDatabase admin blog_ai_db --eval "
print('🔄 Clearing failed processing jobs...');

const result = db.processing_jobs.deleteMany({
  \$or: [
    { status: 'failed' },
    { status: 'cancelled' },
    { 
      status: 'running',
      created_at: { \$lt: new Date(Date.now() - 24*60*60*1000) } // Older than 24 hours
    }
  ]
});

print('✅ Removed', result.deletedCount, 'failed/stuck jobs');
"
```

---

## 🏗️ **Collection Recreation Commands**

### **Recreate Essential Collections**
```bash
# Recreate collections with proper structure and indexes
docker exec selflearning_mongodb mongosh -u admin -p password123 --authenticationDatabase admin blog_ai_db --eval "
print('🏗️ Recreating essential collections...');

// Create collections
db.createCollection('blog_summary');
db.createCollection('blog_qna');
db.createCollection('raw_blog_content');
db.createCollection('blog_meta_data');

// Create indexes for performance
db.blog_summary.createIndex({ 'blog_id': 1 }, { unique: true });
db.blog_summary.createIndex({ 'created_at': -1 });
db.blog_summary.createIndex({ 'main_topics': 1 });

db.blog_qna.createIndex({ 'blog_id': 1 });
db.blog_qna.createIndex({ 'question_type': 1 });
db.blog_qna.createIndex({ 'created_at': -1 });

db.raw_blog_content.createIndex({ 'blog_id': 1 }, { unique: true });
db.raw_blog_content.createIndex({ 'url': 1 });
db.raw_blog_content.createIndex({ 'crawled_at': -1 });

print('✅ Collections and indexes created');
print('📊 Available collections:', db.getCollectionNames());
"
```

---

## 📊 **Database Statistics and Verification**

### **Check Collection Status**
```bash
# Get detailed information about all collections
docker exec selflearning_mongodb mongosh -u admin -p password123 --authenticationDatabase admin blog_ai_db --eval "
print('📊 Database Statistics for blog_ai_db');
print('=' * 50);

db.getCollectionNames().forEach(function(collectionName) {
  const collection = db[collectionName];
  const count = collection.countDocuments();
  const indexes = collection.getIndexes().length;
  
  print('📁', collectionName);
  print('  📄 Documents:', count);
  print('  🔍 Indexes:', indexes);
  
  if (count > 0) {
    const sample = collection.findOne();
    const fields = Object.keys(sample).length;
    print('  🏷️  Fields:', fields);
  }
  print('');
});

// Database-level stats
const stats = db.stats();
print('💾 Database Size:', Math.round(stats.dataSize / 1024 / 1024 * 100) / 100, 'MB');
print('📊 Total Collections:', stats.collections);
print('📄 Total Documents:', stats.objects);
"
```

### **Verify Cleanup Success**
```bash
# Verify that cleanup was successful
docker exec selflearning_mongodb mongosh -u admin -p password123 --authenticationDatabase admin blog_ai_db --eval "
print('✅ Cleanup Verification Report');
print('=' * 40);

const collections = db.getCollectionNames();
let totalDocs = 0;
let emptyCollections = 0;

collections.forEach(function(collection) {
  const count = db[collection].countDocuments();
  totalDocs += count;
  
  if (count === 0) {
    emptyCollections++;
    print('✅', collection, '- CLEAN (0 documents)');
  } else {
    print('📄', collection, '-', count, 'documents remaining');
  }
});

print('');
print('📊 Summary:');
print('  Total Collections:', collections.length);
print('  Empty Collections:', emptyCollections);
print('  Total Documents:', totalDocs);

if (totalDocs === 0) {
  print('🎉 ALL COLLECTIONS ARE CLEAN!');
} else {
  print('⚠️  Some data remains in', (collections.length - emptyCollections), 'collections');
}
"
```

---

## 🚨 **Emergency Commands**

### **Nuclear Option - Drop Entire Database**
```bash
# ⚠️ EXTREME CAUTION: This removes the entire database
docker exec selflearning_mongodb mongosh -u admin -p password123 --authenticationDatabase admin --eval "
print('🚨 NUCLEAR OPTION: Dropping entire blog_ai_db database');
print('⚠️  This action cannot be undone!');

// Switch to the database
use blog_ai_db;

// Show what will be lost
print('📊 Current database contents:');
db.getCollectionNames().forEach(function(collection) {
  const count = db[collection].countDocuments();
  print('  -', collection + ':', count, 'documents');
});

// Drop the database
db.dropDatabase();

print('💥 Database blog_ai_db has been completely removed');
print('📊 Remaining databases:', db.adminCommand('listDatabases').databases.map(d => d.name));
"
```

### **Recreate Database from Scratch**
```bash
# Recreate the database with initial structure
docker exec selflearning_mongodb mongosh -u admin -p password123 --authenticationDatabase admin --eval "
print('🏗️ Recreating blog_ai_db database from scratch...');

// Switch to the database (creates it if it doesn't exist)
use blog_ai_db;

// Run the initialization script
load('/docker-entrypoint-initdb.d/init-db.js');

print('✅ Database recreated with initial structure');
"
```

---

## 💡 **Best Practices**

### **1. Always Backup Before Cleanup**
```bash
# Create a backup before major cleanup operations
docker exec selflearning_mongodb mongodump --username admin --password password123 --authenticationDatabase admin --db blog_ai_db --out /tmp/backup_$(date +%Y%m%d_%H%M%S)
```

### **2. Use Confirmation Prompts**
```bash
# Add confirmation for destructive operations
docker exec selflearning_mongodb mongosh -u admin -p password123 --authenticationDatabase admin blog_ai_db --eval "
const confirm = 'yes';  // Change this to 'yes' to confirm
if (confirm !== 'yes') {
  print('❌ Operation cancelled - change confirm variable to proceed');
  quit();
}
// ... destructive operations here
"
```

### **3. Test on Sample Data First**
```bash
# Test cleanup on a small subset first
docker exec selflearning_mongodb mongosh -u admin -p password123 --authenticationDatabase admin blog_ai_db --eval "
// Test: Remove only 1 document
const result = db.blog_summary.deleteOne({});
print('Test result:', result.deletedCount, 'document removed');
"
```

---

## 🔗 **Related Commands**

- **Start MongoDB**: `cd mongodb && ./scripts/mongodb_setup.sh start`
- **Stop MongoDB**: `cd mongodb && ./scripts/mongodb_setup.sh stop`
- **MongoDB Logs**: `docker logs selflearning_mongodb`
- **Web Interface**: http://localhost:8081 (admin/password123)

---

## 📝 **Notes**

- All commands assume the default setup with:
  - Container name: `selflearning_mongodb`
  - Database: `blog_ai_db`
  - Username: `admin`
  - Password: `password123`
- Always test destructive operations in a development environment first
- Consider creating backups before major cleanup operations
- Use `deleteMany({})` for data cleanup, `drop()` for complete removal
