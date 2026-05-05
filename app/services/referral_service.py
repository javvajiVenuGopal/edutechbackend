from app.senior_guide.models import SeniorGuide


def process_referral_bonus(db, guide):

    # no referral used
    if not guide.referred_by:
        return

    # already credited
    if guide.referral_paid:
        return

    referrer = db.query(SeniorGuide).filter(
        SeniorGuide.referral_code == guide.referred_by
    ).first()

    if not referrer:
        return

    # credit bonus
    referrer.available_balance += 25
    referrer.total_earned += 25

    guide.referral_paid = True

    db.commit()