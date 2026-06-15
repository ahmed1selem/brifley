# Briefly: Project Documentation Summary

Based on the project documentation for "Briefly: AI-Based News Consumption Enhancement System", here is a comprehensive summary of the main points, including the project's overall architecture, UI design, system structure, and data management.

## Project Overview
**Briefly** is an AI-driven web application designed to streamline and personalize news consumption. It addresses the modern challenge of information overload by allowing users to sign up, select their preferred types of news, subscribe to specific feeds, and interact with content.

## Core Features and AI Integration
* **News Classification & Grouping:** The system utilizes various machine learning algorithms (Support Vector Machine, Random Forest Classifier, Naïve Bayes, Gradient Boosting) combined with techniques like TF-IDF and CountVectorization to classify and group similar news articles.
* **Advanced AI Capabilities:** 
  * **Summarization:** Employs state-of-the-art abstractive summarization models like BART (AraBART for Arabic) and PEGASUS for English.
  * **Clustering:** Uses advanced algorithms like K-means, DBSCAN, and UMAP for dimensionality reduction to find patterns and embed articles into vector spaces.
  * **Web Scraping:** Integrates robust scraping tools (BeautifulSoup, Goose3, Newspaper, Selenium) to seamlessly extract public and premium article content.

## User Interface (UI) & Frontend Architecture
* **Technology Stack:** The frontend is a Single-Page Application (SPA) built using **React**, HTML5, CSS3, and modern JavaScript (ES6+).
* **State Management:** Utilizes **Redux Toolkit** for centralized and predictable global state management across the application.
* **Routing:** Implements **React Router** for seamless client-side routing, ensuring fast navigation without full page reloads.
* **Responsive Design:** Employs CSS Box Model, Flexbox, and Grid layouts to create a responsive, flexible user interface that adapts to various devices and screen sizes.
* **User Engagement:** Users can dynamically interact with the UI to read summaries, save articles, express opinions via comments, and "like" articles or replies.

## System & Backend Architecture (Core Points)
The backend is built using **.NET (ASP.NET Core)** and is designed for high performance, modularity, and security. It strictly follows **Clean Architecture** principles, which emphasizes separation of concerns across the following layers:
* **API Layer:** Handles incoming HTTP requests, routing, authentication, and returns responses to the client (Controllers, Middleware, DTOs).
* **Core Layer:** Contains the application-specific business rules and use cases (Commands, Queries, Validators, Mappers).
* **Service Layer:** Bridges the core and infrastructure layers, performing business logic operations without dealing directly with persistence.
* **Infrastructure Layer:** Manages interactions with external systems, including the database, file systems, and external model APIs (Repositories, DbContext).
* **Domain Layer:** The innermost layer containing enterprise-wide business rules (Entities, Aggregates).

**Key Backend Technologies & Responsibilities:**
* **Design Patterns:** Implements the **CQRS (Command Query Responsibility Segregation)** and **Mediator** patterns to efficiently separate read and write operations, centralize communication between components, and enhance scalability.
* **API & Security:** A **RESTful API** handles operations securely, employing **Identity** and **JWT (JSON Web Tokens)** for token-based authentication and OAuth (Google login).
* **Background Processing:** **Hangfire** is heavily utilized to schedule and manage asynchronous background jobs, ensuring the main application remains highly performant. These tasks include:
  * Fetching new articles from subscribed RSS feeds hourly using the **FeedReader** library.
  * Triggering external APIs for AI summaries and clusters daily.
  * Cleaning up storage by deleting articles older than a week.
* **Testing & Documentation:** Emphasizes unit and integration testing, code reviews, and comprehensive API documentation for seamless frontend integration.

## Data Management & Feed Structure
The system uses a **Microsoft SQL Server** database, interacting with it via **Entity Framework (EF) Core** using a **Code First** approach. EF provides powerful capabilities like LINQ to Entities, automatic change tracking, and easy database migrations. The core data structure handles the complex relationships between users, feeds, and articles:
* **RSS Feeds (`RSSes` table):** Stores metadata about available news sources (ID, Title, Description, Link, Image).
* **User Subscriptions (`RssSubscriptions` table):** Maps users to their preferred RSS feeds, allowing customized news aggregation.
* **Articles (`Articles` table):** The central hub for news content. It stores the scraped article Title, Description, Link, Image, the AI-generated `Summarized` text, `Category` (from classification), and metrics like `Likes` and `Views`. Each article is linked to its parent RSS feed (`RSSId`).
* **Interactions:**
  * **Comments (`CommentsArticle` table):** Supports a nested comment structure (`ParentCommentId`) enabling users to reply to one another.
  * **Saved Articles (`SavedArticles` table):** Allows users to bookmark specific articles for later reading.
