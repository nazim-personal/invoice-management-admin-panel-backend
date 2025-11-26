# Flask Billing and Invoice API

This project is a back-end API for a billing and invoicing application built with Python and the Flask micro-framework. It provides a robust and scalable solution for managing customers, products, invoices, and payments.

## Features

- **User Authentication:** Secure user registration and login with JWT-based authentication and 2FA.
- **Customer Management:** CRUD operations for customer profiles.
- **Product Management:** CRUD operations for products and services.
- **Invoice Management:** Create, update, and manage invoices with line items.
- **Payment Processing:** Record payments against invoices.
- **Dashboard:** An overview of key metrics.
- **Role-Based Access Control:** Differentiated access levels for admins, managers, and staff.

## Getting Started

### Prerequisites

- [Nix](https://nixos.org/)
- [Firebase CLI](https://firebase.google.com/docs/cli)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   ```

2. **Navigate to the project directory:**
   ```bash
   cd <project-directory>
   ```

3. **Activate the development environment:**
   The project uses a Nix-based environment. The virtual environment is automatically created at `.venv`.

   To activate the virtual environment, run:
   ```bash
   source .venv/bin/activate
   ```

4. **Install dependencies:**
   The project dependencies are listed in `requirements.txt` and are installed automatically when the workspace is first created. To install them manually, run:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

To start the Flask development server, use the `web` preview task, which executes the `./devserver.sh` script:

```bash
./devserver.sh
```

The API will be available at `http://localhost:5001/api`.

## API Endpoints

A collection of cURL commands for all available endpoints is provided in the `endpoints.sh` file. To use it, first make it executable:

```bash
chmod +x endpoints.sh
```

Then, run the script:

```bash
./endpoints.sh
```

*Note: You will need to replace placeholder values for tokens in the `endpoints.sh` file with actual tokens obtained from the authentication endpoints.*

## Project Structure

```
├── app
│   ├── __init__.py
│   ├── auth
│   ├── blueprints
│   ├── database
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── db_manager.py
│   │   ├── models
│   │   └── schemas
│   ├── static
│   └── templates
├── devserver.sh
├── endpoints.sh
├── requirements.txt
└── run.py
```

- **app/:** The main application module.
  - **auth/:** Contains authentication-related logic.
  - **blueprints/:** Houses the different blueprints for the application (e.g., users, customers, products).
  - **database/:** Manages database connections, schemas, and models.
  - **static/, templates/:** For serving static files and templates (if any).
- **devserver.sh:** Script to run the Flask development server.
- **endpoints.sh:** A shell script with cURL commands to test all API endpoints.
- **requirements.txt:** A list of all Python dependencies.
- **run.py:** The entry point to the application.
