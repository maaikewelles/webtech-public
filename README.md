# Hoofdzaken & Co. Webshop 📚📖

Een simpele Flask webapplicatie gemaakt onder andere met Bootstrap als framework voor het fictieve bedrijf Hoofdzaken & Co. Hoofdzaken & Co. is een boekenhandel die zich specialiseert in zelfhulpboeken. Dit project is de eindopdracht van 1.3 Webtechnologie I 25-26 aan de Hanze.

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
- vervolgens kan je hem openen in je browser: `http://127.0.0.1:5000/`

## Routes

- `/` homepagina
- `/contact` contactpagina
- `/auth` login- en registratiepagina
- `/login` shortcut naar login
- `/register` shortcut naar registratie
- `/profile` profielpagina (vereist login)
- `/orders` eigen bestellingen (vereist login)
- `/admin/orders` overzicht alle bestellingen en CRUD-mogelijkheden (alleen admin)
- `/shop` webshop met filters en paginering
- `/shop/product/<book_id>` productpagina's
- `/search` zoekpagina
- `/gifts` cadeauinspiratie met aantal thema's
- `/cart` winkelmandje
- `/cart/checkout` afrekenen (vereist login)

## Authenticatie

- Maakt gebruik van SQLite `instance/users.db`
- Registratie slaat hashed passwords op
- Login maakt gebruik van session-based authentication
- Flask-Login wordt gebruikt voor beschermde routes
- Formulieren zijn beschermd met CSRF-tokens

## Boeken

- De webshop laadt boeken uit SQLite: `instance/books.db` (database nog niet gerealiseerd)
- De database wordt automatisch aangemaakt en gevuld met de huidige catalogus bij het opstarten
- Product-, overzichts- en zoekpagina’s lezen rechtstreeks uit deze database

## Winkelmandje en bestellingen

- Het winkelmandje werkt met sessies (`cart` in session)
- De aantallen van boeken zijn aanpasbaar in het winkelmandje en totaalprijs wordt automatisch herberekend
- Bij het aanmaken van een bestelling wordt een bestelling met orderregels opgeslagen in `instance/users.db`
- Gebruikers kunnen hun eigen bestellingen bekijken via `/orders`
- Admin kan bestellingen bekijken, status van verzending aanpassen en verwijderen (CRUD) via `/admin/orders`

## Blueprints

- `blueprints/auth.py` voor login, registratie en logout
- `blueprints/account.py` voor profiel, bestellingen en het admin panel met een overzicht van alle bestellingen
- `blueprints/shop.py` voor shop, productpagina, cadeau ideeën en zoekfunctionaliteit
- `blueprints/cart.py` voor het winkelmandje en voor het plaatsen van een bestelling
- `services/` bevat gedeelde logica en databasefuncties (zoals users, books, orders en wishlist) zodat de code overzichtelijk en goed te onderhouden blijft

## Omgevingsvariabelen

- `SECRET_KEY` voor een vaste app secret
- `ADMIN_NAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` voor het admin-account bij initialisatie
- Bij initialisatie van de app is het e-mailadres van Admin admin@hoofdzaken.nl en het wachtwoord is Admin123!

## Overige functionaliteit

- **Profielfoto**: Ingelogde gebruikers kunnen een profielfoto uploaden, wijzigen en verwijderen; JPG, JPEG, PNG, GIF en WEBP worden ondersteund
- **Wishlist**: Gebruikers kunnen boeken toevoegen aan hun persoonlijke wishlist om deze later te bekijken en kopen of verwijderen uit de lijst
- **Shop-filters**: In de webshop kan de gebruiker boeken filteren op genre, taal en prijs
- **Zoekfunctionaliteit**: Een boek kan worden gevonden op basis van titel, auteur en ISBN via de zoekfunctie
- **CSRF-bescherming**: Alle formulieren zijn beveiligd tegen CSRF (Cross-Site Request Forgery) aanvallen door middel van CSRF-tokens

## Bronvermelding

Onderstaande bronnen en documentatie zijn gebruikt om te leren over Flask, Jinja, Bootstrap et cetera naast lesmateriaal vanuit de Hanze.
- [Officiële quickstart documentatie voor Flask](https://flask.palletsprojects.com/en/stable/quickstart/#)
- [Jinja2 templates en forms](https://www.codecademy.com/learn/learn-flask-jinja2-templates-and-forms)
- [Blueprints](https://flask.palletsprojects.com/en/stable/blueprints/)
- [Flash messages met Flask](https://flask.palletsprojects.com/en/stable/patterns/flashing/)
- [Inspiratie voor winkelmandje](https://medium.com/@olikorma/how-i-build-a-shopping-cart-using-python-flask-and-mysql-722bdfb98d1e)
- [Bootstrap: Spacing](https://getbootstrap.com/docs/4.0/utilities/spacing/)
- [Bootstrap: Buttons](https://getbootstrap.com/docs/4.0/components/buttons/)
- [Bootstrap: Cards](https://getbootstrap.com/docs/4.0/components/card/)
- [Bootstrap: Carousel](https://getbootstrap.com/docs/4.0/components/carousel/)
- [Bootstrap: Pagination](https://getbootstrap.com/docs/4.0/components/pagination/)
- [CSRF (Cross-Site Request Forgery)](https://developer.mozilla.org/en-US/docs/Web/Security/Attacks/CSRF)