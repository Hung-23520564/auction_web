# Real-Time Auction Website

**Course**: NT208.P23.ANTT
**Instructor**: Trần Tuấn Dũng
**Group**: 13

## Team Members

* 23520564: Nguyễn Đình Hưng
* 23520648: Trần Quang Huy
* 23520543: Trần Việt Hoàng
* 23520247: Hoàng Quốc Đạt

## Project Description

The Real-Time Auction Website is a platform designed for fair and efficient real-time bidding on products. Sellers can list items, and buyers can place bids live. The system supports secure transactions, virtual currency payments, and user ratings.

## Features

* **Product Listing**: Sellers can create listings by providing product details, starting price, end time, images, description, and item condition.
* **Live Bidding**: Buyers place bids on products in real-time, with instantaneous price updates.
* **Initial Deposit (Stake)**: Buyers must stake a deposit for their first bid. If the bid fails (not highest at auction end), the deposit is automatically refunded.
* **Virtual Currency Wallet**: Users can top up and pay using virtual currency within the platform.
* **User Ratings**: After each transaction, both buyers and sellers can rate and review each other to build trust.
* **Real-Time Price Updates**: Auction prices are pushed live to users through WebSockets.

## How It Works

1. **Listing Creation**: Sellers log in and create a new auction listing with all necessary product details and the starting price.
2. **Bidding Phase**: Registered buyers stake their deposit and place bids. Prices update in real time across all connected clients.
3. **Auction Closing**: When the countdown timer ends, the highest bidder wins. If a buyer’s bid was not highest, their deposit is automatically refunded.
4. **Payment Settlement**: Winners pay the final bid amount using the virtual currency wallet.
5. **Post-Auction Review**: Both parties leave ratings and reviews for each other.

## Demo Links

* **Live Website**: [auctionhub.uk](https://www.auctionhub.uk/)
* **Interview Video**:

  * [Video 1](https://vt.tiktok.com/ZSkvdnGwt/)
  * [Video 2](https://vt.tiktok.com/ZSkvd3kX5/)
  * [Video 3](https://vt.tiktok.com/ZSkvd3aM9/)

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
