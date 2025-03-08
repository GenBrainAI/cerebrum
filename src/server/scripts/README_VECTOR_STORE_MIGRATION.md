# Vector Store Migration

## Overview

This document explains the migration from the custom vector store implementation to using ChromaDB exclusively. The previous implementation used a hybrid approach with both a custom file-based storage system and ChromaDB, which caused confusion and inefficiency.

## Changes Made

1. **VectorStore Class**:
   - Removed custom file-based storage implementation
   - Now uses ChromaDB exclusively for all vector storage operations
   - Changed default base path from `persistent_state/context/vector_store` to `persistent_state/chroma_db`
   - Simplified and improved methods to work directly with ChromaDB

2. **ContextDatabase Class**:
   - Updated to use the same ChromaDB path as VectorStore
   - Removed redundant ChromaDB initialization
   - Updated methods to work with the new VectorStore implementation

3. **ContextProvider Class**:
   - Updated initialization to use the same ChromaDB path for both VectorStore and ContextDatabase
   - Ensured consistent usage of the updated implementations

## Migration Process

A migration script has been created to move data from the old vector store implementation to the new ChromaDB implementation. The script is located at `src/server/scripts/migrate_vector_store.py`.

### How to Run the Migration

1. Make sure you have the latest code with the updated vector store implementation.
2. Run the migration script:

```bash
python src/server/scripts/migrate_vector_store.py
```

3. The script will:
   - Create a backup of the old vector store at `persistent_state/vector_store_backup`
   - Migrate all data from the old vector store to the new ChromaDB implementation
   - Verify the migration was successful
   - Ask if you want to delete the old vector store

### Force Migration

If the target directory already contains data, the script will refuse to run to prevent data loss. You can force the migration with:

```bash
python src/server/scripts/migrate_vector_store.py --force
```

## Verification

After migration, you can verify that the system is using the new implementation by:

1. Checking that the `persistent_state/chroma_db` directory contains your vector data
2. Running a search query and confirming it returns expected results
3. Monitoring the logs to ensure the system is using the correct paths

## Troubleshooting

If you encounter issues after migration:

1. **Missing Data**: Check if the migration completed successfully. You can run the migration script again with the `--force` flag.
2. **Search Not Working**: Ensure the system is using the correct paths. Check the logs for any path-related errors.
3. **Restore from Backup**: If needed, you can restore from the backup at `persistent_state/vector_store_backup`.

## Technical Details

### ChromaDB Structure

The ChromaDB implementation uses collections with the prefix `vs_` to store vector data. Each collection represents a different index or category of data.

### Embedding Generation

Embeddings are generated using OpenAI's embedding API with the `text-embedding-3-small` model. The system will fall back to local embeddings if the OpenAI API is unavailable.

### Data Storage

All vector data is now stored in the ChromaDB format at `persistent_state/chroma_db`. This includes:
- Document content
- Metadata
- Embeddings
- Collection information 