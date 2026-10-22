# Product Specification: Telegram Booking & Salon CRM Bot

## 1. Product Vision & Value Proposition
An automated, turn-key Telegram booking bot designed for service SMBs (barbershops, beauty salons, aesthetic clinics, massage therapists, private tutors). The system provides self-serve booking 24/7 without human dispatcher overhead, prevents double-booking via atomic slot reservation, sends instant admin alerts, and enables CSV customer exporting.

## 2. Core Functional Requirements
- **Interactive Multi-Step Booking Wizard**:
  - Category selection
  - Service selection with duration and transparent pricing
  - Specialist/Master selection (or "Any Available")
  - Dynamic 14-day rolling calendar with working hours checking
  - Real-time slot availability filtering (prevents overbooking)
  - Client contact capture (phone & full name) with phone request button
  - Booking confirmation & unique reference code
- **Client Self-Management**:
  - View existing active appointments
  - 1-click cancellation with slot release and admin notification
  - Price-list lookup
- **Business Admin Panel (/admin)**:
  - Role-based authorization via ADMIN_ID in config
  - Today and upcoming appointment schedule dashboard
  - 1-click CSV/Excel export of bookings and customer CRM list
  - Client broadcast and notification dispatch
- **Data Persistence & Concurrency**:
  - Async SQLite database (`aiosqlite`)
  - Normalized relational schema: `categories`, `services`, `masters`, `bookings`, `users`
  - Seed script for instant demonstration

## 3. Technology Stack
- **Runtime**: Python 3.11+
- **Framework**: aiogram 3.x (FSM, inline keyboards, callback routers)
- **Database**: SQLite3 via aiosqlite
- **Testing**: pytest, pytest-asyncio
- **Packaging**: Docker, Docker Compose

## 4. Monetization Strategies
1. **Turnkey Setup Agency Model**: Sell installation and branding setup to local salons ($200 - $600 one-off).
2. **Managed Cloud Bot Hosting**: Host and maintain bots for monthly retainer ($29 - $59 / month).
3. **Template / Source Code Marketplace**: Sell as ready-made digital asset on Gumroad, CodeCanyon, or GitHub Sponsors.
