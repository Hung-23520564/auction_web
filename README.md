# Real-Time Auction Website

**Course**: NT208.P23.ANTT <br>
**Instructor**: Trần Tuấn Dũng <br>
**Group 13** <br>
Team Members:
- 23520564: Nguyễn Đình Hưng
- 23520648: Trần Quang Huy
- 23520543: Trần Việt Hoàng
- 23520247: Hoàng Quốc Đạt

- **Live Website**: <a href="https://www.auctionhub.uk/" target="_blank">auctionhub.uk</a>

## 📋 Table of Contents
- [Description](#description)
- [Technology Stack](#technology-stack)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [API Documentation](#api-documentation)
- [Deployment](#deployment)
- [Demo Links](#demo-links)
- [License](#license)

## 🎯 Description

The Real-Time Auction Website is a comprehensive platform for fair and fast product bidding in real-time. Built with Django and modern web technologies, it supports multiple users, secure transactions, WebSocket real-time updates, and AI-powered features, ensuring a safe and smooth auction experience.

## 🛠 Technology Stack

### Backend
- **Django 5.x** - Main web framework
- **Django Channels** - WebSocket support for real-time bidding
- **Django REST Framework** - API development
- **PostgreSQL** - Primary relational database
- **Redis** - Caching and WebSocket channel layer
- **Celery** - Background task processing (nếu có)
- **JWT Authentication** - Secure API authentication

### Frontend
- **Bootstrap 5** - UI framework
- **JavaScript (Vanilla)** - Client-side logic
- **WebSocket API** - Real-time communication

### Storage & Media
- **Cloudinary** - Cloud-based image and video management

### Deployment & Infrastructure
- **AWS EC2** - Production application hosting
- **AWS RDS for PostgreSQL** - Managed production database
- **Cloudflare** - CDN, DNS, SSL, and Security Proxy
- **Nginx** - Reverse proxy and static file serving
- **Gunicorn** - WSGI server for handling HTTP requests
- **Daphne** - ASGI server for handling WebSocket connections
- **Ubuntu** - Server operating system
- **Systemd** - Service management on Linux

### Payment Integration
- **VietQR** - Vietnamese QR payment system

## ✨ Features

### Core Auction Features
- **Real-Time Bidding** - Live price updates using WebSocket
- **Countdown Timers** - Visual auction end time tracking
- **Bid History** - Complete bidding history for each item
- **Escrow System** - Secure deposit holding for bidders
- **Auto-bidding** - Automated bidding with customizable strategies

### User Management
- **Email Authentication** - Secure login with email verification
- **Google OAuth** - Social login integration
- **User Profiles** - Customizable profiles with avatar upload
- **Balance Management** - Integrated wallet system

### Payment & Transactions
- **Integrated Wallet** - VietQR payment integration
- **Deposit System** - Required deposits for auction participation
- **Transaction History** - Complete payment tracking
- **Admin Approval** - Manual transaction verification for security

### Advanced Features
- **AI Chatbot** - Real-time customer support (e.g., Kommunicate)
- **Search & Filtering** - Full-text search with PostgreSQL
- **Admin Dashboard** - Comprehensive auction and user management
- **Review System** - User rating and feedback
- **Mobile Responsive** - Optimized for all devices

### Technical Features
- **Production-Ready Stack** - Nginx + Gunicorn + Daphne for high performance
- **SEO Optimized** - Sitemap, robots.txt, and meta tags
- **Enhanced Security** - HTTPS, CSRF, XSS, and SQL Injection protection via Django & Cloudflare
- **Performance Monitoring** - Built-in logging and tracking

## 🏗 Architecture

### Production Deployment Architecture
```
              +----------------------------------+
              |              Users               |
              +-----------------+----------------+
                                | (HTTPS)
              +-----------------v----------------+
              |           Cloudflare             |
              | (DNS, CDN, SSL, DDoS Protection) |
              +-----------------+----------------+
                                | (HTTPS)
+-------------------------------v-------------------------------+
|                   AWS EC2 Instance (Ubuntu)                   |
|                                                               |
|  +---------------------------+                                |
|  |           Nginx           |                                |
|  | (Reverse Proxy, Port 443) |                                |
|  +-------------+-------------+                                |
|                |                                              |
|  +-------------+-------------+                                |
|  |                           | (WebSocket /ws/**)             |
|  |  (HTTP /)                 |                                |
|  |                           |                                |
|  +-------------v--v--+           +------------v-----------+   |
|  |     Gunicorn      |           |          Daphne        |   |
|  | (WSGI App Server) |           |  (ASGI App Server)     |   |
|  +---------+---------+           +----------+-------------+   |
|            |                                |                 |
|            +----------------+---------------+                 |
|                             |                                 |
|                      +------v------+                          |
|                      |   Django    |                          |
|                      | Application |                          |
|                      +--+-------+--+                          |
|                         |       |                             |
+-------------------------+       +-----> AWS RDS (PostgreSQL)  |
                                  |                             |
                                  +-----> Redis (Channel Layer) | 
                                  |                             |
                                  +-----> Cloudinary (Media)    |
                                                                |
+---------------------------------------------------------------+
```

### Application Structure
```
auction_web/
├── apps/
│   ├── auth_users/      # User authentication & profiles
│   ├── items/           # Auction item management
│   ├── bidding/         # Real-time bidding system
│   ├── payments/        # Transaction handling
│   └── ...              # Other feature-specific apps
├── auction_web/
│   ├── static/          # Project-wide static files (CSS, JS)
│   ├── templates/       # Base HTML templates
│   └── settings.py      # Django configuration
│   └── asgi.py          # ASGI entry-point for Daphne
│   └── wsgi.py          # WSGI entry-point for Gunicorn
└── requirements.txt     # Python dependencies
└── manage.py            # Django's command-line utility
```

## 🚀 Installation

### Prerequisites
- Python 3.10+
- PostgreSQL 12+
- Redis
- Git

### 1. Clone Repository
```bash
git clone <repository-url>
cd auction_web
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Setup
Create a `.env` file in the root directory by copying the example:
```bash
nano .env
```
Then, fill in the required variables in the `.env` file.

### 5. Database Setup
Ensure your PostgreSQL server is running and accessible.
```bash
# Apply database migrations
python manage.py migrate

# Create a superuser for the admin panel
python manage.py createsuperuser
```

### 6. Run Development Server
Choose the appropriate command based on your needs:
```bash
# For standard HTTP development (no real-time features)
python manage.py runserver

# For development with real-time WebSocket features
# This command runs the ASGI server directly to handle both HTTP and WebSockets
daphne -p 8000 auction_web.asgi:app
```

## 🔧 Environment Variables

### Required Variables
```bash
# Django
SECRET_KEY=your-super-secret-key
DEBUG=True  # Set to False in production
ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_URL=postgresql://user:password@localhost:5432/auction_db

# Cloudinary (Image Storage)
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# Email Configuration
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-google-app-password

# Google OAuth (Optional)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Redis (Required for production, optional for dev)
REDIS_URL=redis://127.0.0.1:6379/1
```

## 📡 API Documentation

### Authentication Endpoints
```
POST /api/auth/login/          # User login
POST /api/auth/register/       # User registration
POST /api/auth/logout/         # User logout
GET  /api/users/profile/       # Get user profile
PUT  /api/users/profile/       # Update user profile
```

### Auction Endpoints
```
GET  /api/items/               # List all auction items
GET  /api/items/{id}/          # Get auction details
```

### WebSocket Endpoints
```
ws://your-domain/ws/bidding/{item_id}/  # Real-time bidding for an item
ws://your-domain/ws/home/               # General homepage updates
```

*(For a full list of APIs, please refer to the project's Postman collection or Swagger documentation.)*

## 🚀 Deployment

This project is deployed on AWS using a high-performance stack managed by systemd.

### Production Infrastructure
- **AWS EC2 (Ubuntu)**: Hosts the Django application.
- **AWS RDS for PostgreSQL**: Managed, scalable, and reliable database service.
- **Cloudflare**: Acts as the primary entry point, providing CDN, DDoS protection, and SSL termination.
- **Nginx**: Serves as a reverse proxy, directing HTTP traffic to Gunicorn, WebSocket traffic to Daphne, and serving static files directly for maximum speed.
- **Gunicorn**: The WSGI server dedicated to handling synchronous HTTP requests.
- **Daphne**: The ASGI server dedicated to handling asynchronous WebSocket connections.
- **Redis**: Serves as the crucial channel layer backend, enabling communication between different server processes.
- **Systemd**: Manages Gunicorn and Daphne as robust system services, ensuring they are always running.

## 🎬 Demo Links

- **Interview Video**:
  - <a href="https://vt.tiktok.com/ZSkvdnGwt/" target="_blank">Video 1</a>
  - <a href="https://vt.tiktok.com/ZSkvd3kX5/" target="_blank">Video 2</a>
  - <a href="https://vt.tiktok.com/ZSkvd3aM9/" target="_blank">Video 3</a>

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---
**© 2025 Group 13 - NT208.P23.ANTT**
