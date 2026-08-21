import asyncio
from app.db.session import SessionLocal
from app.db.repository import instagram_account_repo, automation_flow_repo, flow_node_repo, flow_edge_repo
from sqlalchemy import select, delete
from app.models.instagram import InstagramAccount
from app.models.automation import AutomationFlow, FlowNode, FlowEdge

async def seed_flow():
    print("Connecting to database...")
    async with SessionLocal() as db:
        # Find the mock account
        account = await instagram_account_repo.get_by_instagram_id(db, "991122")
        if not account:
            print("Mock account @brand_growth (ID: 991122) not found. Run seed_mock_account.py first.")
            return

        print(f"Found Instagram Account: @{account.username} (ID: {account.id})")

        # Clean existing flows for this account to avoid conflicts
        query = select(AutomationFlow).where(AutomationFlow.instagram_account_id == account.id)
        res = await db.execute(query)
        flows = res.scalars().all()
        for f in flows:
            print(f"Deleting existing flow: {f.name} (ID: {f.id})")
            await db.delete(f)
        await db.commit()

        # Create new flow
        flow_id = "mock_flow_1"
        print(f"Seeding automation flow '{flow_id}'...")
        flow = await automation_flow_repo.create(db, obj_in={
            "id": flow_id,
            "instagram_account_id": account.id,
            "name": "New Comment Flow 1",
            "is_active": True
        })
        await db.commit()
        await db.refresh(flow)

        # Create trigger node
        print("Creating trigger node...")
        await flow_node_repo.create(db, obj_in={
            "id": "mock_node_trig_1",
            "flow_id": flow.id,
            "type": "trigger",
            "config": {
                "keywords": ["Guide", "Link", "Best"],
                "exact_word": True
            }
        })

        # Create reply node
        print("Creating reply node...")
        await flow_node_repo.create(db, obj_in={
            "id": "mock_node_rep_1",
            "flow_id": flow.id,
            "type": "action_reply",
            "config": {
                "message": "Thanks for commenting! I just sent the link to your DMs."
            }
        })

        # Create DM node
        print("Creating DM node...")
        await flow_node_repo.create(db, obj_in={
            "id": "mock_node_dm_1",
            "flow_id": flow.id,
            "type": "action_dm",
            "config": {
                "message": "Here is your exclusive guide link: https://fitlife.co/home-guide"
            }
        })

        # Create edge 1: trigger -> reply
        print("Creating edge 1 (trigger -> reply)...")
        await flow_edge_repo.create(db, obj_in={
            "id": "mock_edge_trig_rep_1",
            "flow_id": flow.id,
            "source_node_id": "mock_node_trig_1",
            "target_node_id": "mock_node_rep_1",
            "condition_value": None
        })

        # Create edge 2: reply -> DM
        print("Creating edge 2 (reply -> DM)...")
        await flow_edge_repo.create(db, obj_in={
            "id": "mock_edge_rep_dm_1",
            "flow_id": flow.id,
            "source_node_id": "mock_node_rep_1",
            "target_node_id": "mock_node_dm_1",
            "condition_value": None
        })

        await db.commit()
        print("Automation Flow successfully seeded in database!")

if __name__ == "__main__":
    asyncio.run(seed_flow())
