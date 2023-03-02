class Mt5Utils:
    def __init__(self, mt5) -> None:
        self.mt5 = mt5
    
    def get_history_positions_by_magic_numbers(self,magic_number):
        # get all historical deals
        deals = self.mt5.history_deals_get()

        # filter deals by magic number
        magic_deals = [deal for deal in deals if deal.magic == magic_number]

        if len(magic_deals) > 0:
            # print information about each deal in the list
            for deal in magic_deals:
                print(f"Deal ID: {deal.deal}, Magic Number: {deal.magic}, "
                    f"Symbol: {deal.symbol}, Type: {deal.deal_type}, "
                    f"Volume: {deal.volume}, Price: {deal.price}, "
                    f"Profit: {deal.profit}, Time: {deal.time}")
        else:
            print(f"No historical deals found for magic number {magic_number}")
