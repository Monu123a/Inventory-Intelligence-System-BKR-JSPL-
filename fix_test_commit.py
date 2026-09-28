test_path = "test_amazon_architecture.py"
with open(test_path, "r") as f:
    content = f.read()

content = content.replace("AmazonReconciliationService.process_report_item(db, company_id, mock_report_item)\n    db.refresh(allocation)", "AmazonReconciliationService.process_report_item(db, company_id, mock_report_item)\n    db.commit()\n    db.refresh(allocation)")
content = content.replace("AmazonReconciliationService.process_report_item(db, company_id, mock_report_item_final)\n    db.refresh(allocation)", "AmazonReconciliationService.process_report_item(db, company_id, mock_report_item_final)\n    db.commit()\n    db.refresh(allocation)")
content = content.replace("AmazonReconciliationService.process_report_item(db, company_id, mock_return)\n    db.refresh(allocation)", "AmazonReconciliationService.process_report_item(db, company_id, mock_return)\n    db.commit()\n    db.refresh(allocation)")

# Also fix the cleanup so it deletes event logs first
content = content.replace("db.query(AmazonLiveAllocation)", "from app.models.schema import AmazonOrderEventLog\n    db.query(AmazonOrderEventLog).delete()\n    db.query(AmazonLiveAllocation)")

with open(test_path, "w") as f:
    f.write(content)
