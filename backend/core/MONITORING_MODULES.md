# Monitoring Modules Documentation

This document explains the purpose and intended use of each monitoring module in the system.

## Module Overview

### 1. `backend/core/monitoring.py` - MCP Server Monitoring
**Purpose**: Simple monitoring for tracking MCP server usage.
**Features**:
- Counters for requests to main vs fallback servers
- Tool-specific counters
- Status counters (success, error, rate_limited, etc.)

**Used by**:
- Main MCP server (`backend/mcp/mcp_server.py`)
- Fallback MCP server (`backend/mcp/mcp_server_fallback.py`)
- Monitoring API endpoint (`backend/api/routes/monitoring.py`)

### 2. `backend/core/performance_monitoring.py` - General Performance Monitoring
**Purpose**: General performance monitoring utilities.
**Features**:
- Operation metrics collection
- Performance counters
- Context managers for monitoring operations
- Function decorators for automatic monitoring

**Used by**:
- Services that need to track operation performance
- Components that require detailed timing information

### 3. `backend/services/monitoring.py` - Service-Level Monitoring
**Purpose**: Service-specific monitoring with enhanced features like Supabase logging.
**Features**:
- Wrapper around general performance monitoring with service-specific enhancements
- Integration with Supabase for persistent logging
- Health check utilities

**Used by**:
- Chat processor (`backend/services/chat_processor.py`)
- PubNub job processor (`backend/services/pubnub_job_processor.py`)

### 4. `backend/api/routes/monitoring.py` - Monitoring API Endpoint
**Purpose**: Exposes MCP statistics via API endpoints.
**Features**:
- GET endpoint for retrieving MCP statistics
- POST endpoint for resetting MCP statistics

**Used by**:
- API routing system

## Usage Guidelines

1. **For MCP server monitoring**: Use `backend/core/monitoring.py`
2. **For general performance monitoring**: Use `backend/core/performance_monitoring.py`
3. **For service-level monitoring with Supabase integration**: Use `backend/services/monitoring.py`
4. **For monitoring API endpoints**: Use `backend/api/routes/monitoring.py`

This separation ensures clear responsibilities and prevents duplication while allowing each module to serve its specific purpose.