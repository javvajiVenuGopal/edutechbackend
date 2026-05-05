import razorpay

RAZORPAY_KEY_ID = "your_key_id"
RAZORPAY_KEY_SECRET = "your_key_secret"

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))