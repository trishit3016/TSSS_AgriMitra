"""
Test ICAR Post-Harvest Rules in Neo4j

This test verifies that ICAR post-harvest rules are properly loaded and can be queried
for tomatoes and onions based on environmental conditions.

Requirements: 5.4, 5.5
"""

import pytest
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture(scope="module")
def neo4j_driver():
    """Create Neo4j driver for testing"""
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    if not neo4j_uri or not neo4j_user or not neo4j_password:
        pytest.skip("Neo4j credentials not configured")
    
    driver = GraphDatabase.driver(
        neo4j_uri,
        auth=(neo4j_user, neo4j_password)
    )
    
    yield driver
    
    driver.close()


class TestICARRules:
    """Test ICAR post-harvest rules"""
    
    def test_tomato_rules_exist(self, neo4j_driver):
        """Test that tomato rules are loaded"""
        with neo4j_driver.session() as session:
            result = session.run("""
                MATCH (c:Crop {name: 'Tomato'})-[:HAS_RULE]->(r:SpoilageRule)
                RETURN count(r) as count
            """)
            count = result.single()["count"]
            
            # Should have at least 8 ICAR rules for tomatoes
            assert count >= 8, f"Expected at least 8 tomato rules, got {count}"
    
    def test_onion_rules_exist(self, neo4j_driver):
        """Test that onion rules are loaded"""
        with neo4j_driver.session() as session:
            result = session.run("""
                MATCH (c:Crop {name: 'Onion'})-[:HAS_RULE]->(r:SpoilageRule)
                RETURN count(r) as count
            """)
            count = result.single()["count"]
            
            # Should have at least 9 ICAR rules for onions
            assert count >= 9, f"Expected at least 9 onion rules, got {count}"
    
    def test_rules_have_temperature_ranges(self, neo4j_driver):
        """Test that all rules have valid temperature ranges"""
        with neo4j_driver.session() as session:
            result = session.run("""
                MATCH (r:SpoilageRule)
                WHERE r.temp_min IS NULL OR r.temp_max IS NULL
                   OR r.temp_min > r.temp_max
                RETURN count(r) as invalid_count
            """)
            invalid_count = result.single()["invalid_count"]
            
            assert invalid_count == 0, f"Found {invalid_count} rules with invalid temperature ranges"
    
    def test_rules_have_humidity_ranges(self, neo4j_driver):
        """Test that all rules have valid humidity ranges"""
        with neo4j_driver.session() as session:
            result = session.run("""
                MATCH (r:SpoilageRule)
                WHERE r.humidity_min IS NULL OR r.humidity_max IS NULL
                   OR r.humidity_min > r.humidity_max
                RETURN count(r) as invalid_count
            """)
            invalid_count = result.single()["invalid_count"]
            
            assert invalid_count == 0, f"Found {invalid_count} rules with invalid humidity ranges"
    
    def test_rules_cite_icar_source(self, neo4j_driver):
        """Test that ICAR rules cite the ICAR source"""
        with neo4j_driver.session() as session:
            result = session.run("""
                MATCH (r:SpoilageRule)-[:CITES]->(s:Source {type: 'ICAR_Manual'})
                WHERE r.id STARTS WITH 'icar_'
                RETURN count(r) as count
            """)
            count = result.single()["count"]
            
            # All ICAR rules should cite the ICAR source
            assert count >= 17, f"Expected at least 17 ICAR rules citing ICAR source, got {count}"
    
    def test_query_tomato_high_temp_high_humidity(self, neo4j_driver):
        """Test querying tomato rules for high temperature and high humidity"""
        with neo4j_driver.session() as session:
            # Simulate conditions: 32°C, 90% humidity
            result = session.run("""
                MATCH (c:Crop {name: 'Tomato'})-[:HAS_RULE]->(r:SpoilageRule)
                WHERE $temp >= r.temp_min AND $temp <= r.temp_max
                  AND $humidity >= r.humidity_min AND $humidity <= r.humidity_max
                RETURN r.condition as condition, r.severity as severity, 
                       r.spoilage_time_hours as hours
                ORDER BY r.severity DESC, r.spoilage_time_hours ASC
                LIMIT 1
            """, temp=32.0, humidity=90.0)
            
            record = result.single()
            assert record is not None, "No matching rule found for high temp/humidity"
            assert record["severity"] in ["critical", "high"], f"Expected critical/high severity, got {record['severity']}"
            assert record["hours"] <= 96, f"Expected short spoilage time, got {record['hours']}h"
    
    def test_query_tomato_optimal_conditions(self, neo4j_driver):
        """Test querying tomato rules for optimal storage conditions"""
        with neo4j_driver.session() as session:
            # Simulate optimal conditions: 13°C, 90% humidity
            result = session.run("""
                MATCH (c:Crop {name: 'Tomato'})-[:HAS_RULE]->(r:SpoilageRule)
                WHERE $temp >= r.temp_min AND $temp <= r.temp_max
                  AND $humidity >= r.humidity_min AND $humidity <= r.humidity_max
                RETURN r.condition as condition, r.severity as severity,
                       r.spoilage_time_hours as hours
                ORDER BY r.severity ASC, r.spoilage_time_hours DESC
                LIMIT 1
            """, temp=13.0, humidity=90.0)
            
            record = result.single()
            assert record is not None, "No matching rule found for optimal conditions"
            assert record["severity"] in ["low", "medium"], f"Expected low/medium severity, got {record['severity']}"
            assert record["hours"] >= 168, f"Expected long spoilage time, got {record['hours']}h"
    
    def test_query_onion_high_humidity_sprouting(self, neo4j_driver):
        """Test querying onion rules for high humidity causing sprouting"""
        with neo4j_driver.session() as session:
            # Simulate conditions: 25°C, 90% humidity
            result = session.run("""
                MATCH (c:Crop {name: 'Onion'})-[:HAS_RULE]->(r:SpoilageRule)
                WHERE $temp >= r.temp_min AND $temp <= r.temp_max
                  AND $humidity >= r.humidity_min AND $humidity <= r.humidity_max
                RETURN r.condition as condition, r.severity as severity,
                       r.spoilage_time_hours as hours
                ORDER BY r.severity DESC, r.spoilage_time_hours ASC
                LIMIT 1
            """, temp=25.0, humidity=90.0)
            
            record = result.single()
            assert record is not None, "No matching rule found for high humidity"
            assert record["severity"] == "critical", f"Expected critical severity, got {record['severity']}"
            assert "sprout" in record["condition"].lower() or "humidity" in record["condition"].lower()
    
    def test_query_onion_optimal_cold_storage(self, neo4j_driver):
        """Test querying onion rules for optimal cold storage"""
        with neo4j_driver.session() as session:
            # Simulate optimal cold storage: 2°C, 68% humidity
            result = session.run("""
                MATCH (c:Crop {name: 'Onion'})-[:HAS_RULE]->(r:SpoilageRule)
                WHERE $temp >= r.temp_min AND $temp <= r.temp_max
                  AND $humidity >= r.humidity_min AND $humidity <= r.humidity_max
                RETURN r.condition as condition, r.severity as severity,
                       r.spoilage_time_hours as hours
                ORDER BY r.severity ASC, r.spoilage_time_hours DESC
                LIMIT 1
            """, temp=2.0, humidity=68.0)
            
            record = result.single()
            assert record is not None, "No matching rule found for optimal cold storage"
            assert record["severity"] == "low", f"Expected low severity, got {record['severity']}"
            assert record["hours"] >= 2160, f"Expected very long spoilage time, got {record['hours']}h"
    
    def test_crop_specific_rules_differ(self, neo4j_driver):
        """Test that tomato and onion have different rules for same conditions"""
        with neo4j_driver.session() as session:
            # Query both crops for same conditions: 25°C, 80% humidity
            tomato_result = session.run("""
                MATCH (c:Crop {name: 'Tomato'})-[:HAS_RULE]->(r:SpoilageRule)
                WHERE $temp >= r.temp_min AND $temp <= r.temp_max
                  AND $humidity >= r.humidity_min AND $humidity <= r.humidity_max
                RETURN r.spoilage_time_hours as hours, r.severity as severity
                ORDER BY r.severity DESC, r.spoilage_time_hours ASC
                LIMIT 1
            """, temp=25.0, humidity=80.0)
            
            onion_result = session.run("""
                MATCH (c:Crop {name: 'Onion'})-[:HAS_RULE]->(r:SpoilageRule)
                WHERE $temp >= r.temp_min AND $temp <= r.temp_max
                  AND $humidity >= r.humidity_min AND $humidity <= r.humidity_max
                RETURN r.spoilage_time_hours as hours, r.severity as severity
                ORDER BY r.severity DESC, r.spoilage_time_hours ASC
                LIMIT 1
            """, temp=25.0, humidity=80.0)
            
            tomato_record = tomato_result.single()
            onion_record = onion_result.single()
            
            assert tomato_record is not None, "No tomato rule found"
            assert onion_record is not None, "No onion rule found"
            
            # Tomatoes and onions should have different spoilage characteristics
            # Tomatoes are more perishable than onions
            assert tomato_record["hours"] < onion_record["hours"], \
                f"Tomatoes should spoil faster than onions under same conditions"
    
    def test_severity_levels_exist(self, neo4j_driver):
        """Test that rules have appropriate severity levels"""
        with neo4j_driver.session() as session:
            result = session.run("""
                MATCH (r:SpoilageRule)
                RETURN DISTINCT r.severity as severity
                ORDER BY severity
            """)
            
            severities = [record["severity"] for record in result]
            
            # Should have multiple severity levels
            assert len(severities) >= 3, f"Expected at least 3 severity levels, got {len(severities)}"
            assert "critical" in severities, "Missing 'critical' severity level"
            assert "high" in severities, "Missing 'high' severity level"
            assert "low" in severities or "medium" in severities, "Missing 'low' or 'medium' severity level"
    
    def test_rules_have_source_references(self, neo4j_driver):
        """Test that all rules have source references"""
        with neo4j_driver.session() as session:
            result = session.run("""
                MATCH (r:SpoilageRule)
                WHERE r.source_reference IS NULL OR r.source_reference = ''
                RETURN count(r) as count
            """)
            
            count = result.single()["count"]
            assert count == 0, f"Found {count} rules without source references"
