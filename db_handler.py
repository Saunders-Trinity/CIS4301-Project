from MARIADB_CREDS import DB_CONFIG
from mariadb import connect
from models.LoanHistory import LoanHistory
from models.Waitlist import Waitlist
from models.Book import Book
from models.Loan import Loan
from models.User import User

UFID = "10787144"
FULLNAME = "Saunders, Trinity"

conn = connect(user=DB_CONFIG["username"], password=DB_CONFIG["password"], host=DB_CONFIG["host"],
               database=DB_CONFIG["database"], port=DB_CONFIG["port"])#, collation='utf8mb4_unicode_ci')

cur = conn.cursor()


def add_book(new_book: Book = None):
    """
    new_book - A Book object containing a new book to be inserted into the DB in the Books table.
        new_book and its attributes will never be None.
    """
    cur.execute(
        """
        INSERT INTO Book
        (isbn, title, author, publication_year, publisher, num_owned)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            new_book.isbn,
            new_book.title,
            new_book.author,
            new_book.publication_year,
            new_book.publisher,
            new_book.num_owned
        )
    )


def add_user(new_user: User = None):
    """
    new_user - A User object containing a new user to be inserted into the DB in the Users table.
        new_user and its attributes will never be None.
    """
    cur.execute(
        """
        INSERT INTO User
        (account_id, name, address, phone_number, email)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            new_user.account_id,
            new_user.name,
            new_user.address,
            new_user.phone_number,
            new_user.email
        )
    )


def edit_user(original_account_id: str = None, new_user: User = None):
     cur.execute(
        """
        UPDATE User
        SET account_id = %s,
            name = %s,
            address = %s,
            phone_number = %s,
            email = %s
        WHERE account_id = %s
        """,
        (
            new_user.account_id,
            new_user.name,
            new_user.address,
            new_user.phone_number,
            new_user.email,
            original_account_id
        )
    )


def checkout_book(isbn: str = None, account_id: str = None):
    cur.execute(
        """
        INSERT INTO Loan (isbn, account_id, checkout_date, due_date)
        VALUES (%s, %s, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 2 WEEK))
        """,
        (isbn, account_id)
    )


def waitlist_user(isbn: str = None, account_id: str = None) -> int:
    # Find the next available position in the waitlist
    cur.execute(
        """
        SELECT COALESCE(MAX(place_in_line), 0) + 1
        FROM Waitlist
        WHERE isbn = %s
        """,
        (isbn,)
    )

    next_position = cur.fetchone()[0]

    # Add the user to the waitlist
    cur.execute(
        """
        INSERT INTO Waitlist (isbn, account_id, place_in_line)
        VALUES (%s, %s, %s)
        """,
        (isbn, account_id, next_position)
    )

    return next_position

def update_waitlist(isbn: str = None):
    # Remove the person currently at the front of the waitlist
    cur.execute(
        """
        DELETE FROM Waitlist
        WHERE isbn = %s AND place_in_line = 1
        """,
        (isbn,)
    )

    # Get the remaining users in their current order
    cur.execute(
        """
        SELECT account_id
        FROM Waitlist
        WHERE isbn = %s
        ORDER BY place_in_line
        """,
        (isbn,)
    )

    waitlisted_users = cur.fetchall()

    # Move everyone up one position
    for position, (account_id,) in enumerate(waitlisted_users, start=1):
        cur.execute(
            """
            UPDATE Waitlist
            SET place_in_line = %s
            WHERE isbn = %s AND account_id = %s
            """,
            (position, isbn, account_id)
        )



def return_book(isbn: str = None, account_id: str = None):
    cur.execute(
        """
        SELECT checkout_date, due_date
        FROM Loan
        WHERE isbn = %s AND account_id = %s
        """,
        (isbn, account_id)
    )

    loan = cur.fetchone()

    if loan is None:
        return

    checkout_date, due_date = loan

    cur.execute(
        """
        INSERT INTO LoanHistory
        (isbn, account_id, checkout_date, due_date, return_date)
        VALUES (%s, %s, %s, %s, CURDATE())
        """,
        (isbn, account_id, checkout_date, due_date)
    )

    cur.execute(
        """
        DELETE FROM Loan
        WHERE isbn = %s AND account_id = %s
        """,
        (isbn, account_id)
    )




def grant_extension(isbn: str = None, account_id: str = None):
    cur.execute(
        """
        UPDATE Loan
        SET due_date = DATE_ADD(due_date, INTERVAL 2 WEEK)
        WHERE isbn = %s AND account_id = %s
        """,
        (isbn, account_id)
    )


def get_filtered_books(filter_attributes: Book = None,
                       use_patterns: bool = False,
                       min_publication_year: int = -1,
                       max_publication_year: int = -1) -> list[Book]:
    query = """
        SELECT isbn, title, author, publication_year, publisher, num_owned
        FROM Book
        WHERE 1=1
    """
    params = []

    attributes = [
        ("isbn", filter_attributes.isbn),
        ("title", filter_attributes.title),
        ("author", filter_attributes.author),
        ("publisher", filter_attributes.publisher)
    ]

    for column, value in attributes:
        if value is not None:
            if use_patterns:
                query += f" AND {column} LIKE %s"
            else:
                query += f" AND {column} = %s"
            params.append(value)

    if filter_attributes.publication_year != -1:
        query += " AND publication_year = %s"
        params.append(filter_attributes.publication_year)

    if filter_attributes.num_owned != -1:
        query += " AND num_owned = %s"
        params.append(filter_attributes.num_owned)

    if min_publication_year != -1:
        query += " AND publication_year >= %s"
        params.append(min_publication_year)

    if max_publication_year != -1:
        query += " AND publication_year <= %s"
        params.append(max_publication_year)

    cur.execute(query, tuple(params))

    results = cur.fetchall()

    return [
        Book(
            isbn=row[0],
            title=row[1],
            author=row[2],
            publication_year=row[3],
            publisher=row[4],
            num_owned=row[5]
        )
        for row in results
    ]
    

def get_filtered_users(filter_attributes: User = None, use_patterns: bool = False) -> list[User]:
    query = """
        SELECT account_id, name, address, phone_number, email
        FROM User
        WHERE 1=1
    """
    params = []

    attributes = [
        ("account_id", filter_attributes.account_id),
        ("name", filter_attributes.name),
        ("address", filter_attributes.address),
        ("phone_number", filter_attributes.phone_number),
        ("email", filter_attributes.email)
    ]

    for column, value in attributes:
        if value is not None:
            if use_patterns and column != "account_id":
                query += f" AND {column} LIKE %s"
            else:
                query += f" AND {column} = %s"

            params.append(value)

    cur.execute(query, tuple(params))
    results = cur.fetchall()

    return [
        User(
            account_id=row[0],
            name=row[1],
            address=row[2],
            phone_number=row[3],
            email=row[4]
        )
        for row in results
    ]

def get_filtered_loans(filter_attributes: Loan = None,
                       min_checkout_date: str = None,
                       max_checkout_date: str = None,
                       min_due_date: str = None,
                       max_due_date: str = None) -> list[Loan]:

    query = """
        SELECT isbn, account_id, checkout_date, due_date
        FROM Loan
        WHERE 1=1
    """
    params = []

    # Filter by Loan attributes
    attributes = [
        ("isbn", filter_attributes.isbn),
        ("account_id", filter_attributes.account_id),
        ("checkout_date", filter_attributes.checkout_date),
        ("due_date", filter_attributes.due_date)
    ]

    for column, value in attributes:
        if value is not None:
            query += f" AND {column} = %s"
            params.append(value)

    # Filter by checkout date range
    if min_checkout_date is not None:
        query += " AND checkout_date >= %s"
        params.append(min_checkout_date)

    if max_checkout_date is not None:
        query += " AND checkout_date <= %s"
        params.append(max_checkout_date)

    # Filter by due date range
    if min_due_date is not None:
        query += " AND due_date >= %s"
        params.append(min_due_date)

    if max_due_date is not None:
        query += " AND due_date <= %s"
        params.append(max_due_date)

    cur.execute(query, tuple(params))
    results = cur.fetchall()

    return [
        Loan(
            isbn=row[0],
            account_id=row[1],
            checkout_date=row[2],
            due_date=row[3]
        )
        for row in results
    ]


def get_filtered_loan_histories(filter_attributes: LoanHistory = None,
                                min_checkout_date: str = None,
                                max_checkout_date: str = None,
                                min_due_date: str = None,
                                max_due_date: str = None,
                                min_return_date: str = None,
                                max_return_date: str = None) -> list[LoanHistory]:

    query = """
        SELECT isbn, account_id, checkout_date, due_date, return_date
        FROM LoanHistory
        WHERE 1=1
    """
    params = []

    # Filter by LoanHistory attributes
    attributes = [
        ("isbn", filter_attributes.isbn),
        ("account_id", filter_attributes.account_id),
        ("checkout_date", filter_attributes.checkout_date),
        ("due_date", filter_attributes.due_date),
        ("return_date", filter_attributes.return_date)
    ]

    for column, value in attributes:
        if value is not None:
            query += f" AND {column} = %s"
            params.append(value)

    # Filter by checkout date
    if min_checkout_date is not None:
        query += " AND checkout_date >= %s"
        params.append(min_checkout_date)

    if max_checkout_date is not None:
        query += " AND checkout_date <= %s"
        params.append(max_checkout_date)

    # Filter by due date
    if min_due_date is not None:
        query += " AND due_date >= %s"
        params.append(min_due_date)

    if max_due_date is not None:
        query += " AND due_date <= %s"
        params.append(max_due_date)

    # Filter by return date
    if min_return_date is not None:
        query += " AND return_date >= %s"
        params.append(min_return_date)

    if max_return_date is not None:
        query += " AND return_date <= %s"
        params.append(max_return_date)

    cur.execute(query, tuple(params))
    results = cur.fetchall()

    return [
        LoanHistory(
            isbn=row[0],
            account_id=row[1],
            checkout_date=row[2],
            due_date=row[3],
            return_date=row[4]
        )
        for row in results
    ]


def get_filtered_waitlist(filter_attributes: Waitlist = None,
                          min_place_in_line: int = -1,
                          max_place_in_line: int = -1) -> list[Waitlist]:

    query = """
        SELECT isbn, account_id, place_in_line
        FROM Waitlist
        WHERE 1=1
    """
    params = []

    attributes = [
        ("isbn", filter_attributes.isbn),
        ("account_id", filter_attributes.account_id)
    ]

    for column, value in attributes:
        if value is not None:
            query += f" AND {column} = %s"
            params.append(value)

    # Filter by exact position only when it isn't the default -1
    if filter_attributes.place_in_line != -1:
        query += " AND place_in_line = %s"
        params.append(filter_attributes.place_in_line)

    if min_place_in_line != -1:
        query += " AND place_in_line >= %s"
        params.append(min_place_in_line)

    if max_place_in_line != -1:
        query += " AND place_in_line <= %s"
        params.append(max_place_in_line)

    cur.execute(query, tuple(params))
    results = cur.fetchall()

    return [
        Waitlist(
            isbn=row[0],
            account_id=row[1],
            place_in_line=row[2]
        )
        for row in results
    ]




def number_in_stock(isbn: str = None) -> int:
    """
    isbn - A string containing the ISBN for a book. ISBN will never be None.

    returns the quantity of books available with their ISBN equal to the isbn parameter. The quantity available should be
        calculated as how many copies the branch owns minus how many copies are checked out to users. If the library does
        not own the book, then -1 should be returned.
    """
    cur.execute(
        """
        SELECT num_owned - (
            SELECT COUNT(*)
            FROM Loan
            WHERE Loan.isbn = Book.isbn
        )
        FROM Book
        WHERE isbn = %s
        """,
        (isbn,)
    )

    result = cur.fetchone()

    if result is None:
        return -1

    return result[0]


def place_in_line(isbn: str = None, account_id: str = None) -> int:
    """
    isbn - A string containing the ISBN for a book. ISBN will never be None.
    account_id - A string containing the account id for a user. account_id will never be None.

    returns what place in line the user with the corresponding account_id is in for the book with the corresponding ISBN. If
        the user is not on the waitlist for that book, then -1 should be returned.
    """
    cur.execute(
        """
        SELECT place_in_line
        FROM Waitlist
        WHERE isbn = %s AND account_id = %s
        """,
        (isbn, account_id)
    )

    result = cur.fetchone()

    if result is None:
        return -1

    return result[0]


def line_length(isbn: str = None) -> int:
    """
    isbn - A string containing the ISBN for a book. ISBN will never be None.

    returns how many people are on the waitlist for the book with the corresponding ISBN. e.g. if there are 5 people on the
        waitlist for a book, 5 should be returned. If there is no waitlist for the book, then 0 should be returned.
    """
    cur.execute(
        """
        SELECT COUNT(*)
        FROM Waitlist
        WHERE isbn = %s
        """,
        (isbn,)
    )

    result = cur.fetchone()

    return result[0]


def save_changes():
    """
    Commits all changes made to the db.
    """
    conn.commit()


def close_connection():
    """
    Closes the cursor and connection.
    """
    cur.close()
    conn.close()
