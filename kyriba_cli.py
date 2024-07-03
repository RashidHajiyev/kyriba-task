import os
import logging
from collections import namedtuple

# Create namedtuples for the different record types. Immutable and for gettin easy access.
Header = namedtuple("Header", ["field_id", "name", "surname", "patronymic", "address"])
Transaction = namedtuple("Transaction", ["field_id", "counter", "amount", "currency"])
Footer = namedtuple("Footer", ["field_id", "total_counter", "control_sum"])

# Deafault values that must exist
HEADER_FIELD_ID = "01"
TRANSACTION_FIELD_ID = "02"
FOOTER_FIELD_ID = "03"
LINE_LENGTH = 120
CURRENCY_VALUES = {"USD", "EUR", "GBP", "PLN", "AZN", "TRL"}

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FixedWidthFile:
    def __init__(self, file_path):
        self.file_path = file_path
    
    def read_file(self):
        records = []
        with open(self.file_path, "r") as f:
            lines = f.readlines()
            for line in lines:
                field_id = line[:2]
                if field_id == HEADER_FIELD_ID:
                    records.append(self.parse_header(line))
                elif field_id == TRANSACTION_FIELD_ID:
                    transaction = self.parse_transaction(line)
                    if transaction:
                        records.append(transaction)
                elif field_id == FOOTER_FIELD_ID:
                    records.append(self.parse_footer(line))
        return records
    
    def parse_header(self, line):
        return Header(
            field_id=line[:2],
            name=line[2:30].strip(),
            surname=line[30:60].strip(),
            patronymic=line[60:90].strip(),
            address=line[90:120].strip(),
        )
    
    def parse_transaction(self, line):
        counter_str = line[2:8].strip()
        amount_str = line[8:20].strip()
        currency = line[20:23].strip()
        
        if len(amount_str) != 12 or not amount_str.isdigit():
            logger.error(f"Invalid amount format: {amount_str}")
            return None

        try:
            counter = int(counter_str)
        except ValueError:
            logger.error(f"Invalid transaction counter: {counter_str}")
            return None
        
        if currency not in CURRENCY_VALUES:
            logger.error(f"Invalid currency: {currency}")
            return None
        
        amount = float(amount_str) / 100
        return Transaction(
            field_id=TRANSACTION_FIELD_ID,
            counter=counter,
            amount=amount,
            currency=currency
        )
    
    def parse_footer(self, line):
        total_counter = int(line[2:8].strip())
        control_sum = float(line[8:20].strip()) / 100
        return Footer(
            field_id=FOOTER_FIELD_ID,
            total_counter=total_counter,
            control_sum=control_sum
        )
    
    
    def format_header(self, header):
        return f"{header.field_id}{header.name.ljust(28)}{header.surname.ljust(30)}{header.patronymic.ljust(30)}{header.address.ljust(30)}\n"
    
    def format_transaction(self, transaction):
        return f"{transaction.field_id}{str(transaction.counter).zfill(6)}{str(int(transaction.amount * 100)).zfill(12)}{transaction.currency.ljust(3)}{' ' * 97}\n"
    
    def format_footer(self, footer):
        return f"{footer.field_id}{str(footer.total_counter).zfill(6)}{str(int(footer.control_sum * 100)).zfill(12)}{' ' * 100}\n"

        # str.zfill() is the string function that fills zeros before ltters
        
        
    def write_file(self, records):
        with open(self.file_path, "w") as f:
            for record in records:
                
                if isinstance(record, Header):
                    f.write(self.format_header(record))
                    
                elif isinstance(record, Transaction):
                    f.write(self.format_transaction(record))
                    
                elif isinstance(record, Footer):
                    f.write(self.format_footer(record))
    
        
#______________________________________________________________________________________________________________



# CLI for interacting with fixed-width files
class FixedWidthCLI:
    def __init__(self, file_path):
        self.file = FixedWidthFile(file_path)
    
    
    
    def get_field_value(self, record_type, field_name):
        
        records = self.file.read_file()

        for record in records:
            if isinstance(record, record_type):
                if hasattr(record, field_name):
                    return getattr(record, field_name)
                else:
                    logger.error(f"Field '{field_name}' not found in '{record_type.__name__}'")
                    return None
        logger.error(f"No record of type '{record_type.__name__}' found")
        return None
    
    
    
    def change_field_value(self, record_type, field_name, new_value):
        records = self.file.read_file()
        updated_records = []

        for record in records:
            if isinstance(record, record_type) and hasattr(record, field_name):  # checks that the rocord that sent to change and current record is the same
                updated_record = record._replace(**{field_name: new_value})
                updated_records.append(updated_record)
            else:
                updated_records.append(record)

        self.file.write_file(updated_records)  # Write the updated records back to the file
    
    
    
    def add_transaction(self, counter, amount, currency):
        records = self.file.read_file()

        # Create a new transaction
        new_transaction = Transaction(
            field_id=TRANSACTION_FIELD_ID,
            counter=counter,
            amount=amount,
            currency=currency
        )

        # Insert it before the footer record
        records.insert(-1, new_transaction)
        self.file.write_file(records)
    
    
    
    def validate_file_structure(self):
        records = self.file.read_file()

        # Ensure the first record is a Header
        if not isinstance(records[0], Header):
            logger.error("First record is not a Header.")
            return False
        
        # Check that the last record is a Footer
        if not isinstance(records[-1], Footer):
            logger.error("Last record is not a Footer.")
            return False
        
        # Ensure all records between the Header and Footer are Transactions
        transactions = records[1:-1]
        if not all(isinstance(i, Transaction) for i in transactions):
            logger.error("Some records between the Header and Footer are not Transactions.")
            return False
        
        # Check the total counter in the Footer matches the number of Transactions
        if records[-1].total_counter != len(transactions):
            logger.error("Footer total counter does not match the number of transactions.")
            return False
        
        # Checking the control sum in the Footer
        control_sum = sum([i.amount for i in transactions])
        if round(control_sum, 2) != round(records[-1].control_sum, 2):
            logger.error(f"Footer control sum mismatch. Expected {records[-1].control_sum}, got {control_sum}.")
            return False
        
        logger.info("File structure is valid.")   # using logger to inform about the validation
        return True
    
    
    
    def handle_cli(self):
        while True:
            print("1. Get field value")
            print("2. Change field value")
            print("3. Add transaction")
            print("4. Validate file structure")
            print("5. Exit")
            choice = input("Enter your choice: ")


            if choice == "1":
                record_type = input("Record type (Header, Transaction, Footer): ")
                field_name = input("Field name: ")
                if record_type.lower() == "header":
                    record_type_cls = Header
                elif record_type.lower() == "transaction":
                    record_type_cls = Transaction
                elif record_type.lower() == "footer":
                    record_type_cls = Footer
                else:
                    print("Invalid record type.")
                    continue

                value = self.get_field_value(record_type_cls, field_name)
                if value is not None:
                    print(f"The value of '{field_name}' in '{record_type}' is: {value}")



            elif choice == "2":
                record_type = input("Record type (Header, Transaction, Footer): ")
                field_name = input("Field name: ")
                new_value = input("New value: ")
                if record_type.lower() == "header":
                    self.change_field_value(Header, field_name, new_value)
                elif record_type.lower() == "transaction":
                    self.change_field_value(Transaction, field_name, new_value)
                elif record_type.lower() == "footer":
                    self.change_field_value(Footer, field_name, new_value)



            elif choice == "3":
                counter = int(input("Transaction counter, for example: 1: "))
                amount = float(input("Transaction amount for example: 20.00: ")) * 100
                currency = input("Transaction currency for example: USD: ")
                self.add_transaction(counter, amount, currency)
            
            
            
            elif choice == "4":
                if self.validate_file_structure():
                    print("File structure is valid.")
                else:
                    print("File structure is not valid.")



            elif choice == "5":
                break
            
            else:
                print("Invalid choice. Choose fom given options!")




if __name__ == "__main__":
    path = input("Enter the path to the fixed-width file: ")
    file_path = os.path.abspath(path)
    cli = FixedWidthCLI(file_path)
    cli.handle_cli()
