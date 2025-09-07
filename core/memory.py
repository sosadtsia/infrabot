"""
Memory system using ChromaDB for storing and retrieving task context
"""

import chromadb
from chromadb.errors import NotFoundError
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

class BotMemory:
    """ChromaDB-based memory system for InfraBot"""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize ChromaDB client and collections"""
        if db_path is None:
            db_path = str(Path.home() / ".infrabot" / "memory")

        # Ensure directory exists
        Path(db_path).mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=db_path)

        # Create collections
        self.interactions = self._get_or_create_collection("interactions")
        self.playbooks = self._get_or_create_collection("playbooks")
        self.results = self._get_or_create_collection("results")

    def _get_or_create_collection(self, name: str):
        """Get or create a ChromaDB collection"""
        try:
            return self.client.get_collection(name)
        except (NotFoundError, ValueError):
            return self.client.create_collection(name)

    def store_interaction(self, interaction_type: str, content: str, metadata: Optional[Dict] = None):
        """Store a user interaction or bot response"""
        doc_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        base_metadata = {
            "type": interaction_type,
            "timestamp": timestamp,
        }
        if metadata:
            base_metadata.update(metadata)

        self.interactions.add(
            documents=[str(content)],
            metadatas=[base_metadata],
            ids=[doc_id]
        )

        return doc_id

    def store_playbook_execution(self, task_description: str, playbook_content: str, result: Dict):
        """Store playbook execution results"""
        doc_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        # Store playbook
        playbook_metadata = {
            "task": task_description,
            "timestamp": timestamp,
            "success": result.get("success", False),
            "type": "playbook"
        }

        self.playbooks.add(
            documents=[playbook_content],
            metadatas=[playbook_metadata],
            ids=[doc_id + "_playbook"]
        )

        # Store execution result
        result_metadata = {
            "task": task_description,
            "timestamp": timestamp,
            "success": result.get("success", False),
            "type": "execution_result"
        }

        self.results.add(
            documents=[json.dumps(result, indent=2)],
            metadatas=[result_metadata],
            ids=[doc_id + "_result"]
        )

        return doc_id

    def get_context(self, query: str, limit: int = 5) -> List[Dict]:
        """Get relevant context for a query using semantic search"""
        try:
            # Search interactions for similar past tasks
            interaction_results = self.interactions.query(
                query_texts=[query],
                n_results=limit
            )

            # Search playbooks for relevant past solutions
            playbook_results = self.playbooks.query(
                query_texts=[query],
                n_results=limit
            )

            context = []

            # Process interaction results
            if interaction_results['documents'][0]:
                for i, doc in enumerate(interaction_results['documents'][0]):
                    metadata = interaction_results['metadatas'][0][i]
                    context.append({
                        "type": "interaction",
                        "content": doc,
                        "metadata": metadata,
                        "relevance_score": interaction_results['distances'][0][i] if 'distances' in interaction_results else 1.0
                    })

            # Process playbook results
            if playbook_results['documents'][0]:
                for i, doc in enumerate(playbook_results['documents'][0]):
                    metadata = playbook_results['metadatas'][0][i]
                    context.append({
                        "type": "playbook",
                        "content": doc,
                        "metadata": metadata,
                        "relevance_score": playbook_results['distances'][0][i] if 'distances' in playbook_results else 1.0
                    })

            # Sort by relevance score (lower is better in ChromaDB)
            context.sort(key=lambda x: x.get('relevance_score', 1.0))

            return context[:limit]

        except Exception as e:
            print(f"Error retrieving context: {e}")
            return []

    def get_recent_history(self, limit: int = 10) -> List[Dict]:
        """Get recent task history"""
        try:
            results = self.interactions.get(
                limit=limit,
                where={"type": "user_request"}
            )

            history = []
            if results['documents']:
                for i, doc in enumerate(results['documents']):
                    metadata = results['metadatas'][i]
                    history.append({
                        "content": doc,
                        "metadata": metadata
                    })

            # Sort by timestamp (most recent first)
            history.sort(key=lambda x: x['metadata'].get('timestamp', ''), reverse=True)
            return history

        except Exception as e:
            print(f"Error retrieving history: {e}")
            return []

    def get_successful_playbooks(self, task_pattern: str, limit: int = 3) -> List[Dict]:
        """Get successful playbooks for similar tasks"""
        try:
            results = self.playbooks.query(
                query_texts=[task_pattern],
                n_results=limit,
                where={"success": True}
            )

            playbooks = []
            if results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i]
                    playbooks.append({
                        "content": doc,
                        "metadata": metadata,
                        "task": metadata.get("task", "Unknown")
                    })

            return playbooks

        except Exception as e:
            print(f"Error retrieving successful playbooks: {e}")
            return []

    def clear_memory(self, collection_name: Optional[str] = None):
        """Clear memory (for testing or reset)"""
        try:
            if collection_name:
                self.client.delete_collection(collection_name)
                setattr(self, collection_name, self._get_or_create_collection(collection_name))
            else:
                # Clear all collections
                for collection in ["interactions", "playbooks", "results"]:
                    self.client.delete_collection(collection)
                    setattr(self, collection, self._get_or_create_collection(collection))

        except Exception as e:
            print(f"Error clearing memory: {e}")

    def get_stats(self) -> Dict[str, int]:
        """Get memory statistics"""
        stats = {}
        try:
            stats["interactions"] = self.interactions.count()
            stats["playbooks"] = self.playbooks.count()
            stats["results"] = self.results.count()
        except Exception as e:
            print(f"Error getting stats: {e}")
            stats = {"interactions": 0, "playbooks": 0, "results": 0}

        return stats
