# Feature Specification — CLI Scanner Fixes & Integration

## Problem Statement
The CLI scanner implementation has multiple critical issues preventing proper execution of rule-based scanners against real database data, resulting in errors, mock data usage, and inconsistent behavior.

## Scope
- In Scope:
  - Fix time parameter conversion from CLI strings to datetime objects
  - Fix DataFrame vs list handling in result processing
  - Implement real database query execution instead of mock data
  - Fix column name mapping for query results
  - Resolve database connection issues in rule engine
  - Fix import path problems
  - Add comprehensive error handling and logging
  - Ensure all scanner types work with real data
  - Validate end-to-end CLI functionality with actual market data

- Out of Scope:
  - Database schema changes
  - New scanner types or rule templates
  - Web interface modifications
  - Performance optimizations beyond basic fixes

## User Personas
- **Quantitative Trader**: Needs reliable CLI access to run scanners on real market data for signal generation
- **System Administrator**: Needs robust error handling and logging for production deployment
- **Data Engineer**: Needs proper database integration and query execution

## User Stories
- As a quantitative trader, I want the CLI to execute real database queries so that I can generate accurate trading signals from live market data
- As a system administrator, I want proper error handling and logging so that I can troubleshoot issues in production
- As a data engineer, I want reliable database connections and query execution so that the system performs consistently

## Acceptance Criteria
- Given a CLI scanner command with time parameters, When executed, Then time strings are properly converted to datetime objects without errors
- Given scanner execution with real database data, When results are processed, Then proper column mapping occurs and no 'symbol' key errors occur
- Given database queries, When executed, Then real data is returned instead of mock data and queries complete successfully
- Given CLI commands, When executed, Then all import issues are resolved and no module loading errors occur
- Given scanner execution, When database lock conflicts occur, Then graceful error handling with clear messages is provided
- Given rule execution, When database connections are established, Then proper connection pooling and resource management occurs

## Constraints
- Performance: Must maintain 22% performance improvement over legacy scanners
- Compliance: Must use real data only, no mock or synthetic data
- Environment: Must work in both development and production environments
- Compatibility: Must maintain backward compatibility with existing CLI usage patterns
