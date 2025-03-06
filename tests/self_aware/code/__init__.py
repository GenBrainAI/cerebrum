"""
Tests for Cerebrum's self-modifying code capabilities.

This package contains tests for the code modification components that enable
Cerebrum to safely modify its own code. The tests are organized as follows:

- test_code_modification.py: Unit tests for individual components of the code
  modification system, including:
  - CodeModification: Class for representing code changes
  - CodeModificationEngine: Engine for generating, validating, applying and
    rolling back code modifications
  - StaticAnalyzer: Component for analyzing code quality and safety
  - ModificationValidator: Component for validating code modifications
  - ModificationVersionControl: Component for tracking code changes

- test_code_modification_integration.py: Integration tests that verify the
  end-to-end functionality of the code modification system, including:
  - End-to-end workflow from generating to applying modifications
  - Validator integration with different components
  - Version control integration for tracking and rolling back changes

These tests ensure that Cerebrum can safely modify its own code while
maintaining stability, passing validation checks, and providing rollback
capabilities in case of errors.
""" 