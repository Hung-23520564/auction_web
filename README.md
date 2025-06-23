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

The Real-Time Auction Website is a comprehensive platform for fair and fast product bidding in real-time. Built with Django 5.1.6 and modern web technologies, it supports multiple users, secure transactions, WebSocket real-time updates, and AI-powered features, ensuring a safe and smooth auction experience.

## 🛠 Technology Stack

### Backend
- **Django 5.1.6** - Main web framework
- **Django Channels** - WebSocket support for real-time bidding
- **Django REST Framework** - API development
- **PostgreSQL** - Primary database
- **Redis** - Caching and WebSocket channel layer
- **Celery** - Background task processing
- **JWT Authentication** - Secure API authentication

### Frontend
- **Bootstrap 5** - UI framework
- **WebSocket** - Real-time communication

### Storage & Media
- **Cloudinary** - Image storage and optimization
- **WhiteNoise** - Static file serving

### Deployment
- **AWS EC2** - Production hosting
- **Nginx** - Reverse proxy and static file serving
- **Gunicorn/Uvicorn** - WSGI/ASGI server
- **Vercel** - Alternative deployment option

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
- **Admin Approval** - Manual transaction verification

### Advanced Features
- **AI Chatbot** - Real-time customer support
- **Search & Filtering** - Full-text search with PostgreSQL
- **Admin Dashboard** - Comprehensive auction management
- **Review System** - User rating and feedback
- **Mobile Responsive** - Optimized for all devices

### Technical Features
- **SEO Optimized** - Sitemap, robots.txt, meta tags
- **Security Headers** - CORS, CSRF, XSS protection
- **Performance Monitoring** - Built-in logging and tracking

## 🏗 Architecture

### System Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Frontend    │    │      Django     │    │    Database     │
│   (Bootstrap)   │◄──►│   (REST API)    │◄──►│  (PostgreSQL)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                      │
         │              ┌─────────────────┐             │
         │              │     Redis       │             │
         └─────────────►│   (Cache &      │◄────────────┘
                        │   WebSocket)    │
                        └─────────────────┘
                                 │
                        ┌─────────────────┐
                        │    Cloudinary   │
                        │ (Image Storage) │
                        └─────────────────┘
```

### Application Structure
```
auction_web/
├── apps/
│   ├── auth_users/      # User authentication & profiles
│   ├── items/           # Auction item management
│   ├── bidding/         # Real-time bidding system
│   ├── payments/        # Transaction handling
│   ├── wallet/          # User wallet & VietQR integration
│   ├── reviews/         # User review system
│   ├── chatbot/         # AI customer support
│   ├── dashboard_admin/ # Admin management panel
│   └── sim/             # Image upload simulation
├── auction_web/
│   ├── static/          # Static files (CSS, JS, images)
│   ├── templates/       # HTML templates
│   └── settings.py      # Django configuration
└── requirements.txt     # Python dependencies
```

## 🚀 Installation

### Prerequisites
- Python 3.10+
- PostgreSQL 12+
- Redis (optional, for production WebSocket)
- Node.js (for frontend dependencies)

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
Create `.env` file in root directory:
```bash
cp .env.example .env  # Copy from template
```

### 5. Database Setup
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 6. Collect Static Files
```bash
python manage.py collectstatic
```

### 7. Run Development Server
```bash
# For HTTP only
python manage.py runserver

# For WebSocket support (recommended)
uvicorn auction_web.asgi:application --host 0.0.0.0 --port 8000 --reload
```

## 🔧 Environment Variables

### Required Variables
```bash
# Django
SECRET_KEY=your-secret-key
DEBUG=True  # Set to False in production
DATABASE_URL=postgresql://user:password@localhost:5432/auction_db

# Cloudinary (Image Storage)
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# Email Configuration
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Google OAuth (Optional)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### Production Variables
```bash
# AWS Deployment
AWS_HOST=your-ec2-domain.com
AWS_ALB_HOST=your-alb-domain.amazonaws.com

# Redis (Production WebSocket)
USE_REDIS_CHANNELS=True
REDIS_URL=redis://your-redis-endpoint:6379

# VietQR Payment
VIETQR_CLIENT_ID=your-vietqr-client-id
VIETQR_API_KEY=your-vietqr-api-key
WEBSITE_BANK_ACCOUNT_NO=your-bank-account
WEBSITE_BANK_ACCOUNT_NAME=your-account-name
WEBSITE_BANK_ACQ_ID=your-bank-id
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
POST /api/items/create/        # Create new auction
GET  /api/items/{id}/          # Get auction details
PUT  /api/items/{id}/          # Update auction (owner only)

POST /api/bidding/place-bid/   # Place a bid
GET  /api/bidding/my-bids/     # Get user's bid history
GET  /api/bidding/item/{id}/bids/  # Get item's bid history
```

### Wallet Endpoints
```
GET  /api/wallet/balance/      # Get wallet balance
POST /api/wallet/deposit/      # Initiate deposit
GET  /api/wallet/transactions/ # Get transaction history
```

### WebSocket Endpoints
```
ws://localhost:8000/ws/bidding/{item_id}/  # Real-time bidding
ws://localhost:8000/ws/home/               # Homepage updates
```

## 🎬 Demo Links

- **Interview Video**:
  - <a href="https://vt.tiktok.com/ZSkvdnGwt/" target="_blank">Video 1</a>
  - <a href="https://vt.tiktok.com/ZSkvd3kX5/" target="_blank">Video 2</a>
  - <a href="https://vt.tiktok.com/ZSkvd3aM9/" target="_blank">Video 3</a>

## 🔍 How It Works

1. **User Registration** - Users create accounts with email verification
2. **Auction Creation** - Sellers list items with starting prices and end times  
3. **Deposit System** - Bidders must deposit the starting price to participate
4. **Real-Time Bidding** - WebSocket enables live price updates and bid notifications
5. **Escrow Management** - System holds deposits until auction completion
6. **Payment Processing** - VietQR integration for secure transactions
7. **Review System** - Users can rate each other after transactions

## 📊 Key Metrics

- **Real-time Performance** - WebSocket updates in real-time
- **Security** - JWT authentication + CSRF protection
- **Scalability** - Redis clustering support for high traffic
- **Mobile Responsive** - 100% mobile compatibility
- **SEO Optimized** - Full search engine optimization

## 🛡 Security Features

- **HTTPS Enforcement** - SSL/TLS encryption
- **CSRF Protection** - Cross-site request forgery prevention
- **XSS Protection** - Cross-site scripting prevention
- **SQL Injection Prevention** - Django ORM protection
- **Rate Limiting** - API request throttling
- **Input Validation** - Comprehensive data validation

## 📈 Performance Optimizations

- **Database Indexing** - Optimized query performance
- **Redis Caching** - Fast data retrieval
- **Static File Compression** - Gzip compression
- **Image Optimization** - Cloudinary automatic optimization
- **Lazy Loading** - Progressive content loading

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---
**© 2025 Group 13 - NT208.P23.ANTT**
