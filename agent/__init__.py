import weave
import os
from dotenv import load_dotenv

load_dotenv()

weave.init(os.getenv('WANDB_PROJECT', 'email-agent'))

print("Weave initialized!")