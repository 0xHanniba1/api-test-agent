# User API

## POST /api/users

Create a new user.

**Request Body:**
- name (string, required): User's name
- email (string, required): User's email
- age (integer, optional): User's age

**Response:** 201 Created

## GET /api/users/{id}

Get user by ID.

**Path Parameters:**
- id (integer, required): User ID

**Response:** 200 OK
