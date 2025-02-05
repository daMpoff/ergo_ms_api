def get_users(user_id: int):
    return tuple(
        [
            """
            select
                id,
                username,
                email,
                first_name,
                last_name
            from
                auth_user
            where id = %s
            """,
            tuple([user_id]),
        ]
    )

def get_users_by_name(name: str):
    return tuple(
        [
            f"""
            select
                id,
                username,
                email,
                first_name,
                last_name
            from
                auth_user
            where username = {name}
            """,
            tuple([name]),
        ]
    )