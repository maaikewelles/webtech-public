# Hoofdzaken & Co. Webshop 📚📖

Een simpele Flask webapplicatie gemaakt onder andere met Bootstrap als framework voor het fictieve bedrijf Hoofdzaken & Co. Hoofdzaken & Co. is een boekenhandel die zich specialiseert in zelfhulpboeken. Dit project is de eindopdracht van 1.3 Webtechnologie I aan de Hanze.

## Gebouwd met

<div align="left">
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg" height="40" alt="python logo"  />
  <img width="12" />
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/html5/html5-original.svg" height="40" alt="html5 logo"  />
  <img width="12" />
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/css3/css3-original.svg" height="40" alt="css logo"  />
  <img width="12" />
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/javascript/javascript-original.svg" height="40" alt="javascript logo"  />
  <img width="12" />
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/bootstrap/bootstrap-original.svg" height="40" alt="bootstrap logo"  />
  <img width="12" />
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/flask/flask-original.svg" height="40" alt="flask logo"  />
</div>

## Setup

1. Het maken van een virtual environment:
	`py -m venv .venv`
2. Activeren op Windows PowerShell:
	`.\.venv\Scripts\Activate.ps1`
3. Dependencies installeren:
	`pip install -r requirements.txt`

## Run

1. App opstarten:
	`python app.py`
2. Openen in browser:
	`http://127.0.0.1:5000/`

### run.bat

Een andere, waarschijnlijk een stuk eenvoudige manier qua setup. Run `run.bat` vanuit de project folder. Deze zal:
- `.venv` aanmaken als dit nodig is
- dependencies van `requirements.txt` installeren
- de app opstarten

## Routes

- `/` homepagina
- `/contact` contactpagina
- `/auth` login- en registratiepagina
- `/login` shortcut naar login
- `/register` shortcut naar registratie
- `/profile` profielpagina (vereist login)
- `/orders` eigen bestellingen (vereist login)
- `/admin/orders` alle bestellingen (alleen admin)
- `/shop` webshop met filters en paginering
- `/shop/product/<book_id>` productdetailpagina
- `/search` zoekpagina
- `/gifts` cadeau-inspiratiepagina
- `/cart` winkelmandje
- `/cart/checkout` afrekenen (vereist login)

## Authenticatie

- Maakt gebruik van SQLite `instance/users.db`
- Registratie slaat hashed passwords op
- Login maakt gebruik van session-based authentication
- Flask-Login wordt gebruikt voor beschermde routes
- Formulieren zijn beschermd met CSRF-tokens

## Boeken

- De webshop laadt boeken uit SQLite `instance/books.db`
- De database wordt automatisch aangemaakt en gevuld met de huidige catalogus bij het opstarten
- Product-, overzichts- en zoekpagina’s lezen rechtstreeks uit deze database

## Winkelmandje en bestellingen

- Winkelmandje werkt met sessies (`cart` in session)
- Aantallen zijn aanpasbaar in het winkelmandje
- Bij het aanmaken van een bestelling wordt een bestelling met orderregels opgeslagen in `instance/users.db`
- Gebruikers kunnen hun eigen bestellingen bekijken via `/orders`
- Admin kan bestellingen bekijken, status van verzending aanpassen en verwijderen via `/admin/orders`

## Blueprints

- `blueprints/auth.py` voor login, registratie en logout
- `blueprints/account.py` voor profiel, bestellingen en het admin panel met een overzicht van alle bestellingen
- `blueprints/shop.py` voor shop, productpagina, cadeau ideeën en zoekfunctionaliteit
- `blueprints/cart.py` voor het winkelmandje en voor het plaatsen van een bestelling
- `services/` bevat gedeelde logica en databasefuncties (zoals users, books, orders en wishlist) zodat de code overzichtelijk en goed te onderhouden blijft

## Omgevingsvariabelen

- `SECRET_KEY` voor een vaste app secret
- `ADMIN_NAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` voor het admin-account bij initialisatie
- Bij initialisatie is het e-mailadres admin@hoofdzaken.nl en het wachtwoord is Admin123!