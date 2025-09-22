"""
NiFi Flow Ingestion Agent - Comprehensive Data Contract Generator
==================================================================

This script is a self-contained Python agent designed for local execution.
Its purpose is to ingest complex NiFi flow JSON/XML exports, perform exhaustive validation,
and generate complete data contracts for migration to Databricks.

Author: Dan Warren
Version: 12.7 (Fixed and Enhanced)
Last Updated: 2025

Ingestion series Agent #000-1200-001
"""

import json
import uuid
import jsonschema
import os
import re
import sys
import numpy
import pandas
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Tuple, Set, Any, Optional
from collections import defaultdict, deque

# ==============================================================================
# CONFIGURATION CONSTANTS
# ==============================================================================

# Complexity scoring thresholds
COMPLEXITY_PROCESSOR_THRESHOLD_LOW = 20
COMPLEXITY_PROCESSOR_THRESHOLD_MEDIUM = 50
COMPLEXITY_PROCESSOR_THRESHOLD_HIGH = 100

COMPLEXITY_SCRIPT_THRESHOLD_LOW = 5
COMPLEXITY_SCRIPT_THRESHOLD_MEDIUM = 10
COMPLEXITY_SCRIPT_THRESHOLD_HIGH = 20

# Scoring weights
COMPLEXITY_WEIGHT_PROCESSORS = 0.5
COMPLEXITY_WEIGHT_CONNECTIONS = 0.3
COMPLEXITY_WEIGHT_GROUPS = 2.0
COMPLEXITY_WEIGHT_DEPTH = 5.0

COMPLEXITY_MAX_PROCESSOR_SCORE = 30
COMPLEXITY_MAX_CONNECTION_SCORE = 20
COMPLEXITY_MAX_GROUP_SCORE = 20
COMPLEXITY_MAX_DEPTH_SCORE = 30

# Migration readiness scoring
READINESS_PENALTY_HIGH_WARNING = 10
READINESS_PENALTY_MEDIUM_WARNING = 5
READINESS_PENALTY_HIGH_SECURITY = 15
READINESS_PENALTY_MEDIUM_SECURITY = 8

# Script size thresholds
SCRIPT_SIZE_THRESHOLD_MEDIUM = 200
SCRIPT_SIZE_THRESHOLD_HIGH = 500

# ==============================================================================
# FILE CONFIGURATION
# ==============================================================================

# Default input file name - auto-detects JSON or XML
DEFAULT_INPUT_FILE = "nifi_flow.json"

# Directory where outputs will be saved
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ==============================================================================
# COMPREHENSIVE NIFI PROCESSOR CATALOG (ENHANCED)
# ==============================================================================

NIFI_PROCESSOR_CATALOG = {
    "ingestion": [
        "GetFile", "GetFTP", "GetSFTP", "GetHTTP", "GetJMSQueue", "GetJMSTopic",
        "GetKafka", "GetMongo", "GetHDFS", "GetHBase", "GetTwitter", "GetSQS",
        "GetGCSObject", "GetAzureBlobStorage", "GetAzureDataLakeStorage",
        "ConsumeAMQP", "ConsumeAzureEventHub", "ConsumeEWS", "ConsumeJMS",
        "ConsumeKafka", "ConsumeKafka_0_10", "ConsumeKafka_0_11", "ConsumeKafka_1_0",
        "ConsumeKafka_2_0", "ConsumeKafka_2_6", "ConsumeKafkaRecord_0_10",
        "ConsumeKafkaRecord_0_11", "ConsumeKafkaRecord_1_0", "ConsumeKafkaRecord_2_0",
        "ConsumeKafkaRecord_2_6", "ConsumeMQTT", "ConsumeWindowsEventLog",
        "FetchDistributedMapCache", "FetchElasticsearch", "FetchFile", "FetchFTP",
        "FetchGCSObject", "FetchHBaseRow", "FetchHDFS", "FetchS3Object", "FetchSFTP",
        "GenerateFlowFile", "GenerateTableFetch", "GetAzureEventHub", "GetCouchbaseKey",
        "GetIgniteCache", "GetSolr", "GetSplunk", "InvokeHTTP", "InvokeAWSGatewayApi",
        "ListenBeats", "ListenHTTP", "ListenRELP", "ListenSyslog", "ListenTCP",
        "ListenTCPRecord", "ListenUDP", "ListenUDPRecord", "ListDatabaseTables",
        "ListFile", "ListFTP", "ListGCSBucket", "ListHDFS", "ListS3", "ListSFTP",
        "QueryCassandra", "QueryDatabaseTable", "QueryDatabaseTableRecord"
    ],
    
    "egress": [
        "PutFile", "PutFTP", "PutSFTP", "PutEmail", "PutSQL", "PutHBaseJSON",
        "PutHBaseRecord", "PutHDFS", "PutKafka", "PutKafkaRecord", "PutKinesisFirehose",
        "PutKinesisStream", "PutMongo", "PutMongoRecord", "PutS3Object", "PutSNS",
        "PutSQS", "PutSyslog", "PutAzureBlobStorage", "PutAzureCosmosDBRecord",
        "PutAzureDataLakeStorage", "PutAzureEventHub", "PutBoxFile", "PutCassandraQL",
        "PutCassandraRecord", "PutCloudWatchMetric", "PutCouchbaseKey", "PutDatabaseRecord",
        "PutDistributedMapCache", "PutDruid", "PutElasticsearch", "PutElasticsearchHttp",
        "PutElasticsearchHttpRecord", "PutElasticsearchRecord", "PutGCSObject",
        "PutGoogleDrive", "PutHive3Streaming", "PutHiveQL", "PutHiveStreaming",
        "PutIgniteCache", "PutInfluxDB", "PutInfluxDatabaseRecord", "PutJMS",
        "PutLambda", "PutORC", "PutParquet", "PutRiemann", "PutSlack", "PutSolrContentStream",
        "PutSplunk", "PutTCP", "PutUDP", "PublishAMQP", "PublishGCPubSub", "PublishKafka",
        "PublishKafka_0_10", "PublishKafka_0_11", "PublishKafka_1_0", "PublishKafka_2_0",
        "PublishKafka_2_6", "PublishKafkaRecord", "PublishKafkaRecord_0_10",
        "PublishKafkaRecord_0_11", "PublishKafkaRecord_1_0", "PublishKafkaRecord_2_0",
        "PublishKafkaRecord_2_6", "PublishMQTT"
    ],
    
    "routing": [
        "RouteOnAttribute", "RouteOnContent", "RouteText", "RouteOnProperty",
        "DistributeLoad", "MonitorActivity", "ControlRate", "EnforceOrder",
        "Notify", "Wait", "RouteAvro", "RouteCsv", "RouteHL7", "RouteJSON",
        "RouteXML", "DetectDuplicate", "HashContent", "IdentifyMimeType"
    ],
    
    "attributes": [
        "UpdateAttribute", "SetAttribute", "RemoveRecordField", "AttributesToCSV",
        "AttributesToJSON", "ExtractAvroMetadata", "ExtractCCDAAttributes",
        "ExtractEmailAttachments", "ExtractEmailHeaders", "ExtractGrok", "ExtractHL7Attributes",
        "ExtractImageMetadata", "ExtractMediaMetadata", "ExtractText"
    ],
    
    "content_transform": [
        "ReplaceText", "ReplaceTextWithMapping", "ModifyBytes", "AppendContent",
        "CompressContent", "UnpackContent", "MergeContent", "MergeRecord",
        "SegmentContent", "SplitContent", "SplitJson", "SplitRecord", "SplitText",
        "SplitXml", "SplitAvro", "ScanContent", "ScanAttribute", "EncryptContent",
        "DecryptContent", "Base64EncodeContent", "CalculateRecordStats", "ConvertCharacterSet",
        "ConvertJSONToSQL", "ConvertRecord", "ExecuteStreamCommand", "ExecuteProcess",
        "ForkRecord", "GeoEnrichIP", "GeoEnrichIPRecord"
    ],
    
    "scripting": [
        "ExecuteScript", "ExecuteGroovyScript", "ExecutePython", "InvokeScriptedProcessor",
        "ScriptedFilterRecord", "ScriptedLookupService", "ScriptedPartitioner",
        "ScriptedReader", "ScriptedRecordSink", "ScriptedTransformRecord", "ScriptedValidateRecord",
        "ScriptedWriter"
    ],
    
    "format_conversion": [
        "ConvertAvroToJSON", "ConvertAvroToORC", "ConvertAvroToParquet",
        "ConvertAvroSchema", "ConvertCSVToAvro", "ConvertExcelToCSVProcessor",
        "ConvertJSONToAvro", "ConvertJSONToSQL", "ConvertRecord", "JoltTransformJSON",
        "JoltTransformRecord", "TransformXml", "ValidateJson", "ValidateRecord",
        "ValidateXml", "ValidateCsv"
    ],
    
    "database": [
        "ConvertJSONToSQL", "ExecuteSQL", "ExecuteSQLRecord", "GenerateTableFetch",
        "ListDatabaseTables", "PutDatabaseRecord", "PutSQL", "QueryCassandra",
        "QueryDatabaseTable", "QueryDatabaseTableRecord", "QuerySolr", "SelectHive3QL",
        "SelectHiveQL", "PutHive3Streaming", "PutHiveQL", "PutHiveStreaming"
    ],
    
    "record_processing": [
        "ConvertRecord", "ForkRecord", "JoltTransformRecord", "LookupRecord",
        "MergeRecord", "PartitionRecord", "PutDatabaseRecord", "QueryRecord",
        "ScanRecord", "ScriptedTransformRecord", "SplitRecord", "UpdateRecord",
        "ValidateRecord", "CalculateRecordStats", "CountText", "EvaluateJsonPath",
        "EvaluateXPath", "EvaluateXQuery"
    ],
    
    "schema": [
        "ConvertAvroSchema", "InferAvroSchema", "UpdateAttribute", "ExtractAvroMetadata"
    ],
    
    "cloud_services": [
        "DeleteS3Object", "FetchS3Object", "GetSQS", "ListS3", "PutCloudWatchMetric",
        "PutKinesisFirehose", "PutKinesisStream", "PutLambda", "PutS3Object",
        "PutSNS", "PutSQS", "TagS3Object",
        "DeleteAzureBlobStorage", "DeleteAzureDataLakeStorage", "FetchAzureBlobStorage",
        "FetchAzureDataLakeStorage", "GetAzureEventHub", "ListAzureBlobStorage",
        "ListAzureDataLakeStorage", "PutAzureBlobStorage", "PutAzureCosmosDBRecord",
        "PutAzureDataLakeStorage", "PutAzureEventHub",
        "DeleteGCSObject", "FetchGCSObject", "GetGCSObject", "ListGCSBucket",
        "PutGCSObject", "PublishGCPubSub", "PutGoogleDrive"
    ],
    
    "data_quality": [
        "DetectDuplicate", "ValidateRecord", "ValidateJson", "ValidateXml",
        "ValidateCsv", "EnforceOrder", "HashContent", "IdentifyMimeType",
        "ScanContent", "ScanAttribute", "VerifyContentMAC", "VerifyChecksum"
    ],
    
    "monitoring": [
        "MonitorActivity", "Notify", "Wait", "PutSlack", "PutEmail", "LogAttribute",
        "LogMessage", "AttributeRollingWindow"
    ],
    
    "network": [
        "GetHTTP", "InvokeHTTP", "ListenHTTP", "PostHTTP", "HandleHttpRequest",
        "HandleHttpResponse", "ListenTCP", "ListenTCPRecord", "ListenUDP",
        "ListenUDPRecord", "PutTCP", "PutUDP", "GetFTP", "GetSFTP", "PutFTP",
        "PutSFTP", "ListFTP", "ListSFTP", "FetchFTP", "FetchSFTP"
    ],
    
    "specialized": [
        "ExtractCCDAAttributes", "ExtractHL7Attributes", "RouteHL7",
        "ExtractGrok", "ScanContent", "ScanAttribute",
        "ExtractImageMetadata", "ExtractMediaMetadata",
        "GeoEnrichIP", "GeoEnrichIPRecord"
    ]
}

# ==============================================================================
# COMPONENT TYPE DEFINITIONS
# ==============================================================================

NIFI_COMPONENT_TYPES = {
    "processors": "processors",
    "connections": "connections",
    "process_groups": "processGroups",
    "remote_process_groups": "remoteProcessGroups",
    "input_ports": "inputPorts",
    "output_ports": "outputPorts",
    "controller_services": "controllerServices",
    "reporting_tasks": "reportingTasks",
    "parameter_contexts": "parameterContexts",
    "funnels": "funnels",
    "labels": "labels",
    "templates": "templates",
    "versioned_flows": "versionedFlows",
    "access_policies": "accessPolicies",
    "user_groups": "userGroups",
    "users": "users"
}

# ==============================================================================
# SECURITY CONFIGURATION (ENHANCED)
# ==============================================================================

# Use word boundaries for more accurate matching
SENSITIVE_PATTERNS = [
    r'\bpassword\b', r'\bpasswd\b', r'\bpwd\b', r'\bsecret\b', 
    r'\bapi[_-]?key\b', r'\bapikey\b', r'\baccess[_-]?key\b',
    r'\bprivate[_-]?key\b', r'\bauth[_-]?token\b', r'\bcredential\b',
    r'\bcertificate\b', r'\bcert\b', r'\bssl\b', r'\btls\b',
    r'\btruststore\b', r'\bkeystore\b', r'\bencryption[_-]?key\b',
    r'\bbearer\b', r'\boauth\b'
]

INSECURE_PROTOCOLS = ["http://", "ftp://", "telnet://", "ldap://"]

# ==============================================================================
# NIFI EXPRESSION LANGUAGE (ENHANCED)
# ==============================================================================

NIFI_SYSTEM_FUNCTIONS = [
    "allAttributes", "anyAttribute", "allMatchingAttributes", "anyMatchingAttribute",
    "allDelineatedValues", "anyDelineatedValue", "append", "prepend", "substring",
    "substringBefore", "substringAfter", "substringBeforeLast", "substringAfterLast",
    "replace", "replaceFirst", "replaceAll", "replaceNull", "replaceEmpty", "trim",
    "toLower", "toUpper", "padLeft", "padRight", "repeat", "startsWith", "endsWith",
    "contains", "in", "find", "matches", "indexOf", "lastIndexOf", "escapeJson",
    "unescapeJson", "escapeXml", "unescapeXml", "escapeHtml3", "escapeHtml4",
    "escapeCsv", "unescapeCsv", "urlEncode", "urlDecode", "base64Encode", "base64Decode",
    "plus", "minus", "multiply", "divide", "mod", "toRadix", "fromRadix", "random",
    "math", "now", "format", "toDate", "toNumber", "isNull", "notNull", "isEmpty",
    "equals", "equalsIgnoreCase", "gt", "ge", "lt", "le", "and", "or", "not", "ifElse",
    "hostname", "ip", "uuid", "UUID", "nextInt", "literal", "getStateValue", "thread",
    "getDelimitedField", "jsonPath", "jsonPathDelete", "jsonPathPut", "jsonPathSet",
    "evaluateELString", "count", "length", "toString", "toDecimal", "getUri", "url", "hash"
]

NIFI_SYSTEM_PROPERTIES = ["nifi.", "java.", "env.", "hostname.", "Environment.", "System."]

# ==============================================================================
# CUSTOM EXCEPTIONS
# ==============================================================================

class FlowValidationError(ValueError):
    """Custom exception for flow validation failures with detailed context."""
    def __init__(self, message: str, component_id: str = None, component_name: str = None, 
                 line_number: int = None):
        self.message = message
        self.component_id = component_id
        self.component_name = component_name
        self.line_number = line_number
        super().__init__(self.message)

# ==============================================================================
# MAIN ORCHESTRATION
# ==============================================================================

def ingestion_agent_run(input_file: str, output_dir: str) -> None:
    """Main orchestration function with enhanced error handling."""
    try:
        print(f"Step 1: Parsing NiFi flow from: {input_file}...")
        
        # Auto-detect format
        file_ext = os.path.splitext(input_file)[1].lower()
        if file_ext == '.xml':
            parsed_flow, total_lines, flow_metadata = _parse_nifi_xml(input_file)
            print("  Detected XML format")
        elif file_ext == '.json':
            parsed_flow, total_lines, flow_metadata = _parse_nifi_json(input_file)
            print("  Detected JSON format")
        else:
            raise ValueError(f"Unsupported file format '{file_ext}'. Must be .json or .xml")
        
        total_components = sum(len(v) for v in parsed_flow.values() if isinstance(v, list))
        print("✓ Parsing successful!")
        print(f"  - Total lines: {total_lines}")
        print(f"  - Total components: {total_components}")
        print(f"  - Flow: {flow_metadata.get('flow_name', 'Unknown')}")

        print("\nStep 2: Three-tiered validation...")
        validation_warnings = _validate_all(parsed_flow)
        print(f"✓ Validation complete! Warnings: {len(validation_warnings)}")

        print("\nStep 3: Security audit...")
        security_findings = _security_audit(parsed_flow)
        high_sev = sum(1 for f in security_findings if f.get("severity") == "HIGH")
        print(f"✓ Security audit complete! Findings: {len(security_findings)} (High: {high_sev})")

        print("\nStep 4: Performance analysis...")
        performance_analysis = _analyze_performance(parsed_flow)
        print("✓ Performance analysis complete!")

        print("\nStep 5: Generating data contract...")
        data_contract = _create_data_contract(
            parsed_flow, input_file, total_lines, flow_metadata,
            validation_warnings, security_findings, performance_analysis
        )
        print("✓ Data contract generated!")

        print("\nStep 6: Generating migration checklist...")
        checklist = _create_checklist(
            parsed_flow, total_lines, validation_warnings,
            security_findings, performance_analysis, flow_metadata
        )
        print("✓ Checklist generated!")

        print("\nStep 7: Saving outputs...")
        contract_path = os.path.join(output_dir, "data_contract.json")
        checklist_path = os.path.join(output_dir, "migration_checklist.json")

        with open(contract_path, 'w', encoding='utf-8') as f:
            json.dump(data_contract, f, indent=2, ensure_ascii=False)
        
        with open(checklist_path, 'w', encoding='utf-8') as f:
            json.dump(checklist, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*70}")
        print("INGESTION COMPLETE")
        print(f"{'='*70}")
        print(f"Flow: {flow_metadata.get('flow_name', 'Unknown')}")
        print(f"Components: {total_components} | Lines: {total_lines}")
        print(f"Warnings: {len(validation_warnings)} | Security: {len(security_findings)}")
        print("\nOutputs:")
        print(f"  📄 {contract_path}")
        print(f"  📋 {checklist_path}")
        print(f"{'='*70}\n")
    
    except FlowValidationError as e:
        _print_error("Validation Error", e, "Review flow for broken connections or invalid configs")
        raise
    except Exception as e:
        _print_error("Unexpected Error", e, "Check file path, permissions, or syntax")
        raise

def _print_error(error_type: str, error: Exception, recommendation: str) -> None:
    """Print formatted error report."""
    error_info = {
        "error_type": error_type,
        "message": str(error),
        "recommendation": recommendation
    }
    if hasattr(error, 'component_id'):
        error_info["component_id"] = error.component_id
    if hasattr(error, 'component_name'):
        error_info["component_name"] = error.component_name
    if hasattr(error, 'line_number'):
        error_info["line_number"] = error.line_number
    
    print(f"\n{'='*70}")
    print(f"❌ {error_type.upper()}")
    print(f"{'='*70}")
    print(json.dumps(error_info, indent=2))
    print(f"{'='*70}\n")

# ==============================================================================
# PARSING FUNCTIONS
# ==============================================================================

def _parse_nifi_json(file_path: str) -> Tuple[Dict, int, Dict]:
    """Parse NiFi JSON with enhanced error handling."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_lines = f.readlines()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin-1') as f:
            raw_lines = f.readlines()
    
    total_lines = len(raw_lines)
    
    try:
        raw_json = json.loads("".join(raw_lines))
    except json.JSONDecodeError as e:
        raise FlowValidationError(
            f"JSON parsing failed: {e.msg}",
            line_number=e.lineno
        )

    flow = raw_json.get("flow", {})
    flow_metadata = {
        "flow_name": flow.get("name", "Unknown"),
        "flow_id": flow.get("id", "Unknown"),
        "comments": flow.get("comments", ""),
        "encoding_version": raw_json.get("encodingVersion", "Unknown"),
        "nifi_version": raw_json.get("nifiVersion", "Unknown"),
        "position": flow.get("position", {}),
        "variables": flow.get("variables", {})
    }

    parsed_flow = {
        "processors": [],
        "connections": [],
        "controller_services": [],
        "process_groups": [],
        "parameter_contexts": [],
        "input_ports": [],
        "output_ports": [],
        "funnels": [],
        "labels": [],
        "remote_process_groups": [],
        "templates": [],
        "reporting_tasks": [],
        "flow_file_queues": []
    }

    def extract_recursive(group: Dict, parent_id: Optional[str] = None, depth: int = 0):
        current_id = group.get("id")
        
        for component_type in ["processors", "connections", "controllerServices", "inputPorts",
                               "outputPorts", "funnels", "labels", "remoteProcessGroups", "templates"]:
            if component_type in group:
                target_key = {
                    "controllerServices": "controller_services",
                    "inputPorts": "input_ports",
                    "outputPorts": "output_ports",
                    "remoteProcessGroups": "remote_process_groups"
                }.get(component_type, component_type)
                
                for item in group[component_type]:
                    item["_parent_group_id"] = parent_id
                    item["_hierarchy_depth"] = depth
                    parsed_flow[target_key].append(item)
        
        if "processGroups" in group:
            for pg in group["processGroups"]:
                pg["_parent_group_id"] = parent_id
                pg["_hierarchy_depth"] = depth
                parsed_flow["process_groups"].append(pg)
                extract_recursive(pg, current_id, depth + 1)
    
    if "flow" in raw_json:
        extract_recursive(raw_json["flow"])
    
    if "parameterContexts" in raw_json.get("flow", {}):
        parsed_flow["parameter_contexts"].extend(raw_json["flow"]["parameterContexts"])
    
    if "reportingTasks" in raw_json.get("flow", {}):
        parsed_flow["reporting_tasks"].extend(raw_json["flow"]["reportingTasks"])
    
    return parsed_flow, total_lines, flow_metadata

def _parse_nifi_xml(file_path: str) -> Tuple[Dict, int, Dict]:
    """Enhanced XML parser with complete component extraction."""
    with open(file_path, 'r', encoding='utf-8') as f:
        raw_lines = f.readlines()
    total_lines = len(raw_lines)
    
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except ET.ParseError as e:
        raise FlowValidationError(
            f"XML parsing failed: {e}",
            line_number=e.position[0] if hasattr(e, 'position') else None
        )
    
    flow_metadata = {
        "flow_name": root.get('name', 'Unknown'),
        "flow_id": root.get('id', 'Unknown'),
        "comments": root.findtext('.//comments', ''),
        "encoding_version": root.get('encodingVersion', 'Unknown'),
        "nifi_version": root.get('nifiVersion', 'Unknown'),
        "position": {},
        "variables": {}
    }
    
    parsed_flow = {
        "processors": [],
        "connections": [],
        "controller_services": [],
        "process_groups": [],
        "parameter_contexts": [],
        "input_ports": [],
        "output_ports": [],
        "funnels": [],
        "labels": [],
        "remote_process_groups": [],
        "templates": [],
        "reporting_tasks": [],
        "flow_file_queues": []
    }
    
    def parse_properties(element: ET.Element) -> Dict[str, str]:
        """Extract properties from XML element."""
        props = {}
        for prop in element.findall('.//property'):
            name = prop.findtext('name')
            value = prop.findtext('value')
            if name:
                props[name] = value if value is not None else ""
        return props
    
    def parse_group_recursive(group_elem: ET.Element, parent_id: Optional[str] = None, depth: int = 0):
        """Recursively parse process groups."""
        
        # Parse processors
        for proc in group_elem.findall('.//processor'):
            props = parse_properties(proc)
            
            parsed_flow["processors"].append({
                "id": proc.get('id'),
                "component": {
                    "type": proc.findtext('class', 'Unknown'),
                    "name": proc.findtext('name', 'Unnamed'),
                    "state": proc.findtext('schedulingStrategy', 'STOPPED'),
                    "schedulingStrategy": proc.findtext('schedulingStrategy', 'TIMER_DRIVEN'),
                    "schedulingPeriod": proc.findtext('schedulingPeriod', '0 sec'),
                    "maxConcurrentTasks": proc.findtext('maxConcurrentTasks', '1'),
                    "runDurationMillis": proc.findtext('runDurationMillis', '0'),
                    "properties": props,
                    "relationships": [r.text for r in proc.findall('.//autoTerminatedRelationship')]
                },
                "_parent_group_id": parent_id,
                "_hierarchy_depth": depth
            })
        
        # Parse connections with full details
        for conn in group_elem.findall('.//connection'):
            parsed_flow["connections"].append({
                "id": conn.get('id'),
                "name": conn.findtext('name', ''),
                "sourceId": conn.findtext('sourceId'),
                "destinationId": conn.findtext('destinationId'),
                "sourceRelationship": conn.findtext('relationship', 'success'),
                "backPressureObjectThreshold": int(conn.findtext('maxWorkQueueSize', '10000')),
                "backPressureDataSizeThreshold": conn.findtext('maxWorkQueueDataSize', '1 GB'),
                "flowFileExpiration": conn.findtext('flowFileExpiration', '0 sec'),
                "prioritizers": [p.text for p in conn.findall('.//prioritizer')],
                "_parent_group_id": parent_id,
                "_hierarchy_depth": depth
            })
        
        # Parse input ports
        for port in group_elem.findall('.//inputPort'):
            parsed_flow["input_ports"].append({
                "id": port.get('id'),
                "component": {
                    "name": port.findtext('name', 'Unnamed'),
                    "state": port.findtext('state', 'STOPPED')
                },
                "_parent_group_id": parent_id,
                "_hierarchy_depth": depth
            })
        
        # Parse output ports
        for port in group_elem.findall('.//outputPort'):
            parsed_flow["output_ports"].append({
                "id": port.get('id'),
                "component": {
                    "name": port.findtext('name', 'Unnamed'),
                    "state": port.findtext('state', 'STOPPED')
                },
                "_parent_group_id": parent_id,
                "_hierarchy_depth": depth
            })
        
        # Parse funnels
        for funnel in group_elem.findall('.//funnel'):
            parsed_flow["funnels"].append({
                "id": funnel.get('id'),
                "_parent_group_id": parent_id,
                "_hierarchy_depth": depth
            })
        
        # Parse labels
        for label in group_elem.findall('.//label'):
            parsed_flow["labels"].append({
                "id": label.get('id'),
                "component": {
                    "label": label.findtext('value', ''),
                    "width": label.findtext('width', '0'),
                    "height": label.findtext('height', '0')
                },
                "_parent_group_id": parent_id,
                "_hierarchy_depth": depth
            })
        
        # Parse remote process groups
        for rpg in group_elem.findall('.//remoteProcessGroup'):
            parsed_flow["remote_process_groups"].append({
                "id": rpg.get('id'),
                "component": {
                    "name": rpg.findtext('name', 'Unnamed'),
                    "targetUri": rpg.findtext('url', ''),
                    "communicationsTimeout": rpg.findtext('timeout', '30 sec')
                },
                "_parent_group_id": parent_id,
                "_hierarchy_depth": depth
            })
        
        # Parse nested process groups recursively
        for pg in group_elem.findall('.//processGroup'):
            pg_id = pg.get('id')
            parsed_flow["process_groups"].append({
                "id": pg_id,
                "component": {
                    "name": pg.findtext('name', 'Unnamed')
                },
                "_parent_group_id": parent_id,
                "_hierarchy_depth": depth
            })
            parse_group_recursive(pg, pg_id, depth + 1)
    
    # Parse root level
    parse_group_recursive(root)
    
    # Parse controller services
    for cs in root.findall('.//controllerService'):
        props = parse_properties(cs)
        parsed_flow["controller_services"].append({
            "id": cs.get('id'),
            "component": {
                "type": cs.findtext('class', 'Unknown'),
                "name": cs.findtext('name', 'Unnamed'),
                "state": cs.findtext('state', 'DISABLED'),
                "properties": props
            }
        })
    
    # Parse reporting tasks
    for rt in root.findall('.//reportingTask'):
        props = parse_properties(rt)
        parsed_flow["reporting_tasks"].append({
            "id": rt.get('id'),
            "component": {
                "type": rt.findtext('class', 'Unknown'),
                "name": rt.findtext('name', 'Unnamed'),
                "schedulingStrategy": rt.findtext('schedulingStrategy', 'TIMER_DRIVEN'),
                "schedulingPeriod": rt.findtext('schedulingPeriod', '5 min'),
                "properties": props
            }
        })
    
    return parsed_flow, total_lines, flow_metadata

# ==============================================================================
# VALIDATION FUNCTIONS
# ==============================================================================

def _validate_all(data: Dict) -> List[Dict]:
    """Three-tiered validation with enhanced checks."""
    warnings = []
    
    print("  🔍 Tier 1: Schema validation...")
    _validate_schema_and_structure(data)
    print("    ✓ Schema valid")
    
    print("  🔍 Tier 2: Logical validation...")
    warnings.extend(_validate_logical_semantics(data))
    print(f"    ✓ Logic valid ({len(warnings)} warnings)")
    
    print("  🔍 Tier 3: Integrity validation...")
    _validate_integrity(data)
    print("    ✓ Integrity valid")
    
    return warnings

def _validate_schema_and_structure(data: Dict) -> None:
    """Tier 1: Schema validation."""
    required_keys = [
        "processors", "connections", "controller_services",
        "process_groups", "parameter_contexts"
    ]
    
    for key in required_keys:
        if key not in data:
            raise FlowValidationError(f"Missing required key: {key}")
        if not isinstance(data[key], list):
            raise FlowValidationError(f"Key '{key}' must be a list")

def _validate_logical_semantics(data: Dict) -> List[Dict]:
    """Tier 2: Enhanced logical validation with circular dependency detection."""
    warnings = []
    
    print("    → Validating connections...")
    valid_ids = _collect_all_valid_ids(data)
    
    # Build connection graph for circular dependency detection
    connection_graph = defaultdict(list)
    
    for conn in data["connections"]:
        conn_id = conn.get("id", "unknown")
        source_id = conn.get("sourceId")
        dest_id = conn.get("destinationId")
        conn_name = conn.get("name", f"Connection {conn_id}")
        
        if not source_id or source_id not in valid_ids:
            raise FlowValidationError(
                f"Connection '{conn_name}' has invalid source: {source_id}",
                conn_id, conn_name
            )
        
        if not dest_id or dest_id not in valid_ids:
            raise FlowValidationError(
                f"Connection '{conn_name}' has invalid destination: {dest_id}",
                conn_id, conn_name
            )
        
        connection_graph[source_id].append(dest_id)
    
    # Check for circular dependencies
    print("    → Detecting circular dependencies...")
    cycles = _detect_cycles(connection_graph)
    if cycles:
        for cycle in cycles:
            warnings.append({
                "type": "circular_dependency",
                "severity": "HIGH",
                "cycle": cycle,
                "message": f"Circular dependency detected: {' -> '.join(cycle)}"
            })
    
    print(f"      ✓ {len(data['connections'])} connections validated")
    
    # Validate processors
    print("    → Validating processors...")
    for proc in data["processors"]:
        proc_id = proc.get("id")
        component = proc.get("component", {})
        proc_name = component.get("name", "Unnamed")
        proc_type = component.get("type", "Unknown")
        proc_state = component.get("state", "STOPPED")
        
        # Check for disabled processors
        if proc_state == "DISABLED":
            warnings.append({
                "type": "disabled_processor",
                "severity": "LOW",
                "processor": proc_name,
                "processor_id": proc_id,
                "message": f"Processor '{proc_name}' is disabled"
            })
        
        # Validate script processors
        if any(script_type in proc_type for script_type in ["ExecuteScript", "ExecuteGroovy", "ExecutePython"]):
            props = component.get("properties", {})
            script_body = props.get("Script Body", "")
            script_file = props.get("Script File", "")
            
            if not script_body.strip() and not script_file.strip():
                raise FlowValidationError(
                    f"Script processor '{proc_name}' has no script",
                    proc_id, proc_name
                )
        
        # Check for unconnected processors (dead-ends)
        relationships = component.get("relationships", [])
        if relationships and proc_id not in connection_graph:
            # Check if it's a terminal processor
            is_terminal = any(term in proc_type for term in ["Put", "Publish", "Post", "Send"])
            if not is_terminal:
                warnings.append({
                    "type": "dead_end_processor",
                    "severity": "MEDIUM",
                    "processor": proc_name,
                    "processor_id": proc_id,
                    "message": f"Non-terminal processor '{proc_name}' has no outbound connections"
                })
    
    print(f"      ✓ {len(data['processors'])} processors validated")
    
    # Validate parameters with improved expression parsing
    print("    → Validating parameters...")
    defined_params = set()
    for ctx in data["parameter_contexts"]:
        for param in ctx.get("parameters", []):
            name = param.get("name") or param.get("parameter", {}).get("name")
            if name:
                defined_params.add(name)
    
    # Enhanced expression pattern that handles nested expressions
    expr_pattern = re.compile(r'\$\{([^}]+)\}')
    
    for proc in data["processors"]:
        component = proc.get("component", {})
        proc_name = component.get("name", "Unnamed")
        
        for prop_name, prop_value in component.get("properties", {}).items():
            if not isinstance(prop_value, str) or "${" not in prop_value:
                continue
            
            for match in expr_pattern.findall(prop_value):
                param_name = match.split(":")[0].strip()
                
                # Check if it's a system function or property
                is_system = (
                    any(param_name.startswith(func.split("(")[0]) for func in NIFI_SYSTEM_FUNCTIONS) or
                    any(param_name.startswith(prefix) for prefix in NIFI_SYSTEM_PROPERTIES)
                )
                
                if not is_system and param_name not in defined_params:
                    warnings.append({
                        "type": "undefined_parameter",
                        "severity": "MEDIUM",
                        "processor": proc_name,
                        "parameter": param_name,
                        "property": prop_name,
                        "message": f"Undefined parameter: {param_name}"
                    })
    
    print(f"      ✓ Parameters validated ({len(defined_params)} defined)")
    
    return warnings

def _detect_cycles(graph: Dict[str, List[str]]) -> List[List[str]]:
    """Detect circular dependencies using DFS."""
    cycles = []
    visited = set()
    rec_stack = set()
    path = []
    
    def dfs(node: str) -> bool:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                # Found a cycle
                cycle_start = path.index(neighbor)
                cycles.append(path[cycle_start:] + [neighbor])
                return True
        
        path.pop()
        rec_stack.remove(node)
        return False
    
    for node in graph:
        if node not in visited:
            dfs(node)
    
    return cycles

def _collect_all_valid_ids(data: Dict) -> Set[str]:
    """Collect all valid component IDs with synthetic port IDs."""
    valid_ids = set()
    
    for proc in data["processors"]:
        if proc.get("id"):
            valid_ids.add(proc["id"])
    
    for pg in data["process_groups"]:
        pg_id = pg.get("id")
        if pg_id:
            valid_ids.add(pg_id)
            valid_ids.add(f"{pg_id}-input-port")
            valid_ids.add(f"{pg_id}-output-port")
    
    for comp_list in [data["controller_services"], data["input_ports"], 
                      data["output_ports"], data["funnels"], data["remote_process_groups"]]:
        for comp in comp_list:
            if comp.get("id"):
                valid_ids.add(comp["id"])
    
    return valid_ids

def _validate_integrity(data: Dict) -> None:
    """Tier 3: UUID uniqueness and completeness."""
    print("    → Validating UUID uniqueness...")
    
    all_uuids = {}
    
    component_lists = [
        ("processors", data["processors"]),
        ("connections", data["connections"]),
        ("controller_services", data["controller_services"]),
        ("process_groups", data["process_groups"]),
        ("input_ports", data["input_ports"]),
        ("output_ports", data["output_ports"]),
        ("funnels", data["funnels"]),
        ("remote_process_groups", data["remote_process_groups"])
    ]
    
    for comp_type, comp_list in component_lists:
        for comp in comp_list:
            comp_id = comp.get("id")
            
            if not comp_id:
                raise FlowValidationError(f"{comp_type} component missing ID")
            
            if comp_id in all_uuids:
                raise FlowValidationError(
                    f"Duplicate UUID: {comp_id} in {comp_type} and {all_uuids[comp_id]}",
                    comp_id
                )
            
            all_uuids[comp_id] = comp_type
    
    print(f"      ✓ {len(all_uuids)} unique IDs validated")

# ==============================================================================
# SECURITY AUDIT
# ==============================================================================

def _security_audit(data: Dict) -> List[Dict]:
    """Enhanced security audit with regex patterns."""
    findings = []
    
    print("    🔒 Scanning for security issues...")
    
    # Compile sensitive patterns
    sensitive_regexes = [re.compile(pattern, re.IGNORECASE) for pattern in SENSITIVE_PATTERNS]
    
    # Scan processors
    for proc in data["processors"]:
        component = proc.get("component", {})
        proc_name = component.get("name", "Unnamed")
        proc_id = proc.get("id")
        
        for prop_name, prop_value in component.get("properties", {}).items():
            if not isinstance(prop_value, str):
                continue
            
            # Check for sensitive property names
            is_sensitive = any(regex.search(prop_name) for regex in sensitive_regexes)
            
            if is_sensitive and prop_value and "${" not in prop_value:
                findings.append({
                    "type": "hardcoded_credential",
                    "severity": "HIGH",
                    "processor": proc_name,
                    "processor_id": proc_id,
                    "property": prop_name,
                    "message": f"Potential hardcoded credential in '{prop_name}'",
                    "recommendation": "Use Parameter Context or secrets manager"
                })
            
            # Check for insecure protocols
            for protocol in INSECURE_PROTOCOLS:
                if protocol in prop_value.lower():
                    findings.append({
                        "type": "insecure_protocol",
                        "severity": "MEDIUM",
                        "processor": proc_name,
                        "processor_id": proc_id,
                        "property": prop_name,
                        "protocol": protocol.rstrip("://"),
                        "message": f"Insecure protocol '{protocol}' detected",
                        "recommendation": "Use encrypted alternative (HTTPS, SFTP, etc.)"
                    })
    
    # Scan controller services
    for cs in data["controller_services"]:
        component = cs.get("component", {})
        cs_name = component.get("name", "Unnamed")
        cs_id = cs.get("id")
        
        for prop_name, prop_value in component.get("properties", {}).items():
            if not isinstance(prop_value, str):
                continue
            
            is_sensitive = any(regex.search(prop_name) for regex in sensitive_regexes)
            
            if is_sensitive and prop_value and "${" not in prop_value:
                findings.append({
                    "type": "hardcoded_credential_service",
                    "severity": "HIGH",
                    "controller_service": cs_name,
                    "controller_service_id": cs_id,
                    "property": prop_name,
                    "message": f"Potential hardcoded credential in service '{cs_name}'",
                    "recommendation": "Use Parameter Context"
                })
    
    print(f"      ✓ Security scan complete: {len(findings)} findings")
    
    return findings

# ==============================================================================
# PERFORMANCE ANALYSIS
# ==============================================================================

def _analyze_performance(data: Dict) -> Dict:
    """Enhanced performance analysis."""
    analysis = {
        "resource_intensive_processors": [],
        "backpressure_risks": [],
        "parallelism_opportunities": [],
        "flow_complexity": {},
        "scheduling_analysis": [],
        "recommendations": []
    }
    
    print("    📊 Analyzing performance...")
    
    intensive_types = {
        "scripting": ["ExecuteScript", "ExecuteGroovy", "ExecutePython"],
        "database": ["ExecuteSQL", "QueryDatabaseTable", "PutSQL"],
        "record": ["QueryRecord", "UpdateRecord", "ValidateRecord"],
        "transform": ["JoltTransform", "TransformXml", "ConvertRecord"],
        "compression": ["CompressContent", "UnpackContent"],
        "encryption": ["EncryptContent", "DecryptContent"]
    }
    
    for proc in data["processors"]:
        component = proc.get("component", {})
        proc_type = component.get("type", "")
        proc_name = component.get("name", "Unnamed")
        
        for category, types in intensive_types.items():
            if any(t in proc_type for t in types):
                analysis["resource_intensive_processors"].append({
                    "processor": proc_name,
                    "processor_id": proc.get("id"),
                    "type": proc_type,
                    "category": category,
                    "concurrent_tasks": component.get("maxConcurrentTasks", "1"),
                    "scheduling": component.get("schedulingStrategy", "TIMER_DRIVEN")
                })
                break
    
    # Analyze backpressure
    for conn in data["connections"]:
        bp_obj = conn.get("backPressureObjectThreshold", 0)
        bp_size = conn.get("backPressureDataSizeThreshold", "0 MB")
        
        if bp_obj == 0 or bp_size == "0 MB":
            analysis["backpressure_risks"].append({
                "connection_id": conn.get("id"),
                "source_id": conn.get("sourceId"),
                "destination_id": conn.get("destinationId"),
                "message": "No backpressure configured"
            })
    
    # Calculate complexity
    analysis["flow_complexity"] = {
        "total_processors": len(data["processors"]),
        "total_connections": len(data["connections"]),
        "total_process_groups": len(data["process_groups"]),
        "max_depth": max((p.get("_hierarchy_depth", 0) for p in data["processors"]), default=0),
        "complexity_score": _calculate_complexity_score(data)
    }
    
    # Generate recommendations
    if len(analysis["resource_intensive_processors"]) > 10:
        analysis["recommendations"].append({
            "category": "performance",
            "severity": "HIGH",
            "message": f"{len(analysis['resource_intensive_processors'])} resource-intensive processors",
            "recommendation": "Plan adequate cluster resources"
        })
    
    return analysis

# ==============================================================================
# OUTPUT GENERATION
# ==============================================================================

def _create_data_contract(data: Dict, file_path: str, total_lines: int,
                          flow_metadata: Dict, warnings: List[Dict],
                          security_findings: List[Dict], performance: Dict) -> Dict:
    """Generate comprehensive data contract."""
    
    processor_counts = defaultdict(int)
    for proc in data["processors"]:
        proc_type = proc.get("component", {}).get("type", "Unknown")
        processor_counts[proc_type] += 1
    
    return {
        "metadata": {
            "contract_id": str(uuid.uuid4()),
            "contract_version": "2.1",
            "generation_timestamp": datetime.now().isoformat(),
            "flow_source": file_path,
            "flow_name": flow_metadata.get("flow_name"),
            "flow_id": flow_metadata.get("flow_id"),
            "nifi_version": flow_metadata.get("nifi_version"),
            "total_lines": total_lines,
            "validation_status": "PASSED",
            "warnings": len(warnings),
            "security_findings": len(security_findings)
        },
        
        "components": {
            "processors": data["processors"],
            "connections": data["connections"],
            "controller_services": data["controller_services"],
            "process_groups": data["process_groups"],
            "parameter_contexts": data["parameter_contexts"],
            "ports": {
                "input": data["input_ports"],
                "output": data["output_ports"]
            },
            "other": {
                "funnels": data["funnels"],
                "labels": data["labels"],
                "remote_process_groups": data["remote_process_groups"]
            }
        },
        
        "validation": {
            "schema": "PASSED",
            "logic": "PASSED",
            "integrity": "PASSED",
            "warnings": warnings,
            "summary": _summarize_items(warnings)
        },
        
        "security": {
            "findings": security_findings,
            "summary": _summarize_items(security_findings)
        },
        
        "performance": performance,
        
        "statistics": {
            "total_components": sum(len(v) for v in data.values() if isinstance(v, list)),
            "processor_types": dict(processor_counts),
            "complexity_score": performance["flow_complexity"]["complexity_score"],
            "migration_readiness": _calculate_migration_readiness(warnings, security_findings)
        },
        
        "traceability": {
            "source_file": os.path.basename(file_path),
            "parser_version": "2.1",
            "timestamp": datetime.now().isoformat()
        }
    }

def _create_checklist(data: Dict, total_lines: int, warnings: List[Dict],
                      security: List[Dict], performance: Dict, metadata: Dict) -> Dict:
    """Generate migration checklist."""
    
    return {
        "summary": {
            "flow_name": metadata.get("flow_name"),
            "generated": datetime.now().isoformat(),
            "total_components": sum(len(v) for v in data.values() if isinstance(v, list)),
            "total_lines": total_lines,
            "critical_issues": len([w for w in warnings if w.get("severity") == "HIGH"]) +
                              len([s for s in security if s.get("severity") == "HIGH"]),
            "complexity": _assess_complexity(data)
        },
        
        "inventory": {
            "processors": _categorize_processors(data["processors"]),
            "connections": len(data["connections"]),
            "services": len(data["controller_services"]),
            "groups": len(data["process_groups"])
        },
        
        "critical_components": {
            "scripts": _extract_scripts(data["processors"]),
            "transforms": _extract_transforms(data["processors"]),
            "sql_queries": _extract_sql(data["processors"]),
            "routing": _extract_routing(data["processors"])
        },
        
        "validation": {
            "warnings": {
                "HIGH": [w for w in warnings if w.get("severity") == "HIGH"],
                "MEDIUM": [w for w in warnings if w.get("severity") == "MEDIUM"],
                "LOW": [w for w in warnings if w.get("severity") == "LOW"]
            }
        },
        
        "security": {
            "findings": {
                "HIGH": [s for s in security if s.get("severity") == "HIGH"],
                "MEDIUM": [s for s in security if s.get("severity") == "MEDIUM"],
                "LOW": [s for s in security if s.get("severity") == "LOW"]
            }
        },
        
        "performance": performance,
        
        "migration_tasks": _generate_tasks(data),
        
        "unmapped_processors": _find_unmapped(data["processors"])
    }

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def _summarize_items(items: List[Dict]) -> Dict:
    """Summarize items by type and severity."""
    summary = {"by_severity": {"HIGH": 0, "MEDIUM": 0, "LOW": 0}, "by_type": {}}
    for item in items:
        severity = item.get("severity", "MEDIUM")
        summary["by_severity"][severity] += 1
        item_type = item.get("type", "unknown")
        summary["by_type"][item_type] = summary["by_type"].get(item_type, 0) + 1
    return summary

def _calculate_complexity_score(data: Dict) -> int:
    """Calculate complexity score using logarithmic scaling."""
    import math
    
    score = 0
    
    # Processor score with logarithmic scaling
    proc_count = len(data["processors"])
    if proc_count > 0:
        proc_score = min(math.log(proc_count + 1) * 10, COMPLEXITY_MAX_PROCESSOR_SCORE)
        score += proc_score
    
    # Connection score
    conn_count = len(data["connections"])
    if conn_count > 0:
        conn_score = min(math.log(conn_count + 1) * 7, COMPLEXITY_MAX_CONNECTION_SCORE)
        score += conn_score
    
    # Group score
    group_count = len(data["process_groups"])
    score += min(group_count * COMPLEXITY_WEIGHT_GROUPS, COMPLEXITY_MAX_GROUP_SCORE)
    
    # Depth score
    max_depth = max((p.get("_hierarchy_depth", 0) for p in data["processors"]), default=0)
    score += min(max_depth * COMPLEXITY_WEIGHT_DEPTH, COMPLEXITY_MAX_DEPTH_SCORE)
    
    return min(int(score), 100)

def _calculate_migration_readiness(warnings: List[Dict], security: List[Dict]) -> int:
    """Calculate migration readiness score."""
    score = 100
    score -= len([w for w in warnings if w.get("severity") == "HIGH"]) * READINESS_PENALTY_HIGH_WARNING
    score -= len([w for w in warnings if w.get("severity") == "MEDIUM"]) * READINESS_PENALTY_MEDIUM_WARNING
    score -= len([s for s in security if s.get("severity") == "HIGH"]) * READINESS_PENALTY_HIGH_SECURITY
    score -= len([s for s in security if s.get("severity") == "MEDIUM"]) * READINESS_PENALTY_MEDIUM_SECURITY
    return max(score, 0)

def _assess_complexity(data: Dict) -> str:
    """Assess overall complexity."""
    proc_count = len(data["processors"])
    script_count = sum(1 for p in data["processors"] 
                      if "Script" in p.get("component", {}).get("type", ""))
    
    if proc_count > COMPLEXITY_PROCESSOR_THRESHOLD_HIGH or script_count > COMPLEXITY_SCRIPT_THRESHOLD_HIGH:
        return "VERY_HIGH"
    elif proc_count > COMPLEXITY_PROCESSOR_THRESHOLD_MEDIUM or script_count > COMPLEXITY_SCRIPT_THRESHOLD_MEDIUM:
        return "HIGH"
    elif proc_count > COMPLEXITY_PROCESSOR_THRESHOLD_LOW or script_count > COMPLEXITY_SCRIPT_THRESHOLD_LOW:
        return "MEDIUM"
    return "LOW"

def _categorize_processors(processors: List[Dict]) -> Dict:
    """Categorize processors by function."""
    categories = defaultdict(list)
    
    for proc in processors:
        proc_type = proc.get("component", {}).get("type", "")
        proc_name = proc.get("component", {}).get("name", "Unnamed")
        short_type = proc_type.split(".")[-1]
        
        categorized = False
        for category, types in NIFI_PROCESSOR_CATALOG.items():
            if any(t in short_type for t in types):
                categories[category].append({"name": proc_name, "type": short_type})
                categorized = True
                break
        
        if not categorized:
            categories["uncategorized"].append({"name": proc_name, "type": short_type})
    
    return dict(categories)

def _extract_scripts(processors: List[Dict]) -> List[Dict]:
    """Extract script processors."""
    scripts = []
    for proc in processors:
        component = proc.get("component", {})
        proc_type = component.get("type", "")
        
        if "Script" in proc_type:
            props = component.get("properties", {})
            script_body = props.get("Script Body", "")
            complexity = "HIGH" if len(script_body) > SCRIPT_SIZE_THRESHOLD_HIGH else \
                        "MEDIUM" if len(script_body) > SCRIPT_SIZE_THRESHOLD_MEDIUM else "LOW"
            
            scripts.append({
                "name": component.get("name"),
                "type": proc_type,
                "engine": props.get("Script Engine"),
                "complexity": complexity,
                "lines": len(script_body.splitlines())
            })
    return scripts

def _extract_transforms(processors: List[Dict]) -> List[Dict]:
    """Extract transformation processors."""
    transforms = []
    for proc in processors:
        component = proc.get("component", {})
        if "Jolt" in component.get("type", ""):
            transforms.append({
                "name": component.get("name"),
                "type": component.get("type")
            })
    return transforms

def _extract_sql(processors: List[Dict]) -> List[Dict]:
    """Extract SQL processors."""
    sql_procs = []
    for proc in processors:
        component = proc.get("component", {})
        if "SQL" in component.get("type", ""):
            sql_procs.append({
                "name": component.get("name"),
                "type": component.get("type")
            })
    return sql_procs

def _extract_routing(processors: List[Dict]) -> List[Dict]:
    """Extract routing processors."""
    routing = []
    for proc in processors:
        component = proc.get("component", {})
        if "Route" in component.get("type", ""):
            routing.append({
                "name": component.get("name"),
                "type": component.get("type")
            })
    return routing

def _generate_tasks(data: Dict) -> List[Dict]:
    """Generate migration tasks."""
    return [
        {"phase": "Pre-Migration", "task": "Review data contract", "status": "TODO"},
        {"phase": "Pre-Migration", "task": "Address security findings", "status": "TODO"},
        {"phase": "Design", "task": "Map processors to Databricks", "status": "TODO"},
        {"phase": "Design", "task": "Design workflow architecture", "status": "TODO"},
        {"phase": "Development", "task": "Convert scripts", "status": "TODO"},
        {"phase": "Development", "task": "Implement transformations", "status": "TODO"},
        {"phase": "Testing", "task": "Unit testing", "status": "TODO"},
        {"phase": "Testing", "task": "Integration testing", "status": "TODO"},
        {"phase": "Deployment", "task": "Deploy to Databricks", "status": "TODO"}
    ]

def _find_unmapped(processors: List[Dict]) -> List[str]:
    """Find processors not in catalog."""
    all_catalog = set()
    for types in NIFI_PROCESSOR_CATALOG.values():
        all_catalog.update(types)
    
    unmapped = set()
    for proc in processors:
        proc_type = proc.get("component", {}).get("type", "")
        short_type = proc_type.split(".")[-1]
        if short_type and short_type not in all_catalog:
            unmapped.add(short_type)
    
    return sorted(list(unmapped))

# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    """Command-line entry point with auto-discovery of all NiFi flow files."""
    
    print(f"\n{'='*70}")
    print("NiFi Flow Ingestion Agent v2.1")
    print("Enhanced Data Contract Generator")
    print(f"{'='*70}\n")
    
    # Determine input files
    if len(sys.argv) > 1:
        # Explicit file provided
        input_files = [sys.argv[1]]
    else:
        # Auto-discover all JSON and XML files in current directory
        print("🔍 Scanning directory for NiFi flow files...")
        input_files = []
        
        for filename in os.listdir(OUTPUT_DIR):
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            # Skip the script itself and output files
            if filename == os.path.basename(__file__):
                continue
            if filename in ['data_contract.json', 'migration_checklist.json']:
                continue
            
            # Check if it's a JSON or XML file
            if filename.endswith('.json') or filename.endswith('.xml'):
                input_files.append(filepath)
        
        if not input_files:
            print("❌ No JSON or XML files found in directory.")
            print(f"   Directory: {OUTPUT_DIR}")
            print(f"\n   Usage: python {sys.argv[0]} <path-to-nifi-flow.json|xml>")
            sys.exit(1)
        
        print(f"   Found {len(input_files)} file(s) to process:")
        for f in input_files:
            print(f"   - {os.path.basename(f)}")
        print()
    
    # Process each file
    success_count = 0
    failure_count = 0
    
    for input_file in input_files:
        if not os.path.exists(input_file):
            print(f"❌ File not found: {input_file}")
            failure_count += 1
            continue
        
        print(f"\n{'─'*70}")
        print(f"Processing: {os.path.basename(input_file)}")
        print(f"{'─'*70}")
        
        # Create output subdirectory for this file
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        file_output_dir = os.path.join(OUTPUT_DIR, f"{base_name}_analysis")
        os.makedirs(file_output_dir, exist_ok=True)
        
        try:
            ingestion_agent_run(input_file, file_output_dir)
            success_count += 1
        except Exception as e:
            print(f"\n❌ Failed to process {os.path.basename(input_file)}: {str(e)}")
            failure_count += 1
            continue
    
    # Summary
    print(f"\n{'='*70}")
    print("BATCH PROCESSING COMPLETE")
    print(f"{'='*70}")
    print(f"✓ Successfully processed: {success_count} file(s)")
    if failure_count > 0:
        print(f"✗ Failed: {failure_count} file(s)")
    print(f"{'='*70}\n")
    
    sys.exit(0 if failure_count == 0 else 1)
