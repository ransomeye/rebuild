# Path and File Name : /home/ransomeye/rebuild/ransomeye_correlation/engine/graph_store.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Persistence layer using SQLAlchemy for graph_nodes and graph_edges tables in Postgres

import os
import json
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from contextlib import contextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class GraphNode(Base):
    """SQLAlchemy model for graph nodes."""
    __tablename__ = 'graph_nodes'
    
    id = Column(String(64), primary_key=True)  # SHA256 hash
    type = Column(String(50), nullable=False)
    value = Column(String(512), nullable=False)
    label = Column(String(512), nullable=False)
    first_seen = Column(DateTime, nullable=False)
    last_seen = Column(DateTime, nullable=False)
    alert_count = Column(Integer, default=0)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class GraphEdge(Base):
    """SQLAlchemy model for graph edges."""
    __tablename__ = 'graph_edges'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    start_node_id = Column(String(64), ForeignKey('graph_nodes.id'), nullable=False, index=True)
    end_node_id = Column(String(64), ForeignKey('graph_nodes.id'), nullable=False, index=True)
    first_seen = Column(DateTime, nullable=False)
    last_seen = Column(DateTime, nullable=False)
    alert_count = Column(Integer, default=0)
    alert_ids_json = Column(Text, nullable=True)  # JSON array of alert IDs
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class GraphStore:
    """
    Persistence layer for graph data in PostgreSQL.
    """
    
    def __init__(self):
        """Initialize graph store."""
        self.engine = None
        self.SessionLocal = None
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize database connection."""
        db_host = os.environ.get('DB_HOST', 'localhost')
        db_port = os.environ.get('DB_PORT', '5432')
        db_name = os.environ.get('DB_NAME', 'ransomeye')
        db_user = os.environ.get('DB_USER', 'gagan')
        db_pass = os.environ.get('DB_PASS', 'gagan')
        
        connection_string = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        
        try:
            self.engine = create_engine(connection_string, pool_pre_ping=True, echo=False)
            self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
            
            # Create tables
            Base.metadata.create_all(bind=self.engine)
            logger.info("Graph store database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self.engine is not None
    
    @contextmanager
    def get_session(self):
        """Context manager for database sessions."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def save_graph(self, graph_state: dict):
        """
        Save graph state to database.
        
        Args:
            graph_state: Graph state dictionary
        """
        with self.get_session() as session:
            # Save nodes
            for node_id, node_data in graph_state.get('nodes', []):
                node_meta = graph_state.get('node_metadata', {}).get(node_id, {})
                
                # Check if node exists
                existing = session.query(GraphNode).filter_by(id=node_id).first()
                
                if existing:
                    # Update existing
                    existing.type = node_data.get('type', existing.type)
                    existing.value = node_data.get('value', existing.value)
                    existing.label = node_data.get('label', existing.label)
                    if node_meta.get('last_seen'):
                        existing.last_seen = datetime.fromisoformat(node_meta['last_seen'].replace('Z', '+00:00'))
                    existing.alert_count = node_meta.get('alert_count', existing.alert_count)
                else:
                    # Create new
                    first_seen = datetime.utcnow()
                    if node_meta.get('first_seen'):
                        try:
                            first_seen = datetime.fromisoformat(node_meta['first_seen'].replace('Z', '+00:00'))
                        except:
                            pass
                    
                    node = GraphNode(
                        id=node_id,
                        type=node_data.get('type', 'Unknown'),
                        value=node_data.get('value', ''),
                        label=node_data.get('label', ''),
                        first_seen=first_seen,
                        last_seen=first_seen,
                        alert_count=node_meta.get('alert_count', 0)
                    )
                    session.add(node)
            
            # Save edges
            for edge in graph_state.get('edges', []):
                if len(edge) < 2:
                    continue
                
                start_id = edge[0]
                end_id = edge[1]
                edge_key = (start_id, end_id)
                edge_meta = graph_state.get('edge_metadata', {}).get(edge_key, {})
                
                # Check if edge exists
                existing = session.query(GraphEdge).filter_by(
                    start_node_id=start_id,
                    end_node_id=end_id
                ).first()
                
                if existing:
                    # Update existing
                    if edge_meta.get('last_seen'):
                        existing.last_seen = datetime.fromisoformat(edge_meta['last_seen'].replace('Z', '+00:00'))
                    existing.alert_count = edge_meta.get('alert_count', existing.alert_count)
                    existing.alert_ids_json = json.dumps(edge_meta.get('alert_ids', []))
                else:
                    # Create new
                    first_seen = datetime.utcnow()
                    if edge_meta.get('first_seen'):
                        try:
                            first_seen = datetime.fromisoformat(edge_meta['first_seen'].replace('Z', '+00:00'))
                        except:
                            pass
                    
                    edge_obj = GraphEdge(
                        start_node_id=start_id,
                        end_node_id=end_id,
                        first_seen=first_seen,
                        last_seen=first_seen,
                        alert_count=edge_meta.get('alert_count', 0),
                        alert_ids_json=json.dumps(edge_meta.get('alert_ids', []))
                    )
                    session.add(edge_obj)
            
            logger.info("Graph state saved to database")
    
    def get_incident_graph(self, incident_id: str) -> dict:
        """
        Get graph data for an incident.
        
        Args:
            incident_id: Incident identifier
            
        Returns:
            Graph data dictionary
        """
        # This would typically query by incident_id
        # For now, return all graph data
        with self.get_session() as session:
            nodes = session.query(GraphNode).all()
            edges = session.query(GraphEdge).all()
            
            graph_data = {
                'nodes': [
                    {
                        'id': node.id,
                        'type': node.type,
                        'value': node.value,
                        'label': node.label,
                        'alert_count': node.alert_count
                    }
                    for node in nodes
                ],
                'edges': [
                    {
                        'start_id': edge.start_node_id,
                        'end_id': edge.end_node_id,
                        'alert_count': edge.alert_count
                    }
                    for edge in edges
                ]
            }
            
            return graph_data
    
    def get_stats(self) -> dict:
        """
        Get graph statistics.
        
        Returns:
            Statistics dictionary
        """
        with self.get_session() as session:
            node_count = session.query(GraphNode).count()
            edge_count = session.query(GraphEdge).count()
            
            return {
                'total_nodes': node_count,
                'total_edges': edge_count
            }

