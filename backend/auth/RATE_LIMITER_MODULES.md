# Rate Limiter Modules Documentation

This document explains the purpose and intended use of each rate limiter module in the system.

## Module Overview

### 1. `backend/auth/mcp_rate_limiter.py` - MCP-Specific Rate Limiting
**Purpose**: Rate limiting for MCP tools to prevent resource exhaustion.
**Features**:
- Tool-specific rate limits
- Configurable limits per tool
- Per-identifier tracking (IP, session, etc.)

**Used by**:
- Main MCP server (`backend/mcp/mcp_server.py`)

### 2. `backend/auth/fallback_rate_limiter.py` - Fallback MCP Rate Limiting
**Purpose**: Rate limiter for fallback MCP server with no external dependencies.
**Features**:
- Same functionality as MCP rate limiter but designed for fallback scenarios
- No external dependencies
- Resilient implementation for fallback situations

**Used by**:
- Fallback MCP server (`backend/mcp/mcp_server_fallback.py`)

### 3. `backend/auth/rate_limiting.py` - General Rate Limiting
**Purpose**: Simple in-memory rate limiter for general API protection.
**Status**: Currently not actively used in the codebase.
**Features**:
- Simple rate limiting based on identifiers
- Configurable request limits and time windows

**Intended Use**:
- Could be used for general API endpoint protection
- Could be integrated with authentication middleware

### 4. `backend/core/guardrails.py` - Guardrails Rate Limiter
**Purpose**: Simple rate limiter as part of guardrails for chat API protection.
**Features**:
- Integrated with PII detection
- Simple in-memory rate limiting
- Designed specifically for chat API protection

**Used by**:
- Chat API route (`backend/api/routes/chat.py`)

## Usage Guidelines

1. **For MCP tool rate limiting**: Use `backend/auth/mcp_rate_limiter.py` (main server) or `backend/auth/fallback_rate_limiter.py` (fallback server)
2. **For general API protection**: Consider using or repurposing `backend/auth/rate_limiting.py`
3. **For chat API protection**: Use the rate limiter in `backend/core/guardrails.py`
4. **For new rate limiting needs**: Evaluate existing modules before creating new ones

## Consolidation Strategy

To reduce confusion and maintain consistency:

1. Keep the specialized rate limiters for their specific purposes:
   - MCP rate limiters for MCP servers
   - Guardrails rate limiter for chat protection

2. Either:
   - Deprecate `backend/auth/rate_limiting.py` if not needed
   - Repurpose it for general API protection with clear documentation

3. Maintain clear boundaries between rate limiting concerns:
   - MCP tool protection vs. general API protection vs. chat protection

This approach maintains the necessary specialization while reducing redundancy and clarifying intended use.