import boto3
import sys
import threading


monitored_machines = {}
c = threading.Condition()


def monitor(tsh):

    instance_types = ['m4.large', 'xlarge', '2xlarge']
    region = 'us-west-2'
    turned_off = []

    client = boto3.client('ec2', region)
    ec2 = boto3.resource('ec2', region)

    filters = [{'Name': 'instance-type', 'Values': ['m4.large', 'xlarge', '2xlarge']},
               {'Name': 'instance-state-name', 'Values': ['running']}]

    instances = ec2.instances.filter(filters)

    for ins_type in instance_types:
        monitored_machines[ins_type] = False

    try:
        price_monitor = PricingThread(tsh, instance_types, region, client, instances)
        monitored_machins = price_monitor.start()
    except RuntimeError:
        exit("Error, unable to start new thread")

    while True:
        instances = ec2.instances.filter(filters)

        c.wait()
        c.acquire()
        for instance in instances:
            if monitored_machins[instance.instance_type]:
                instance.id.stop()
                turned_off.append(instance)

        for instance in turned_off:
            if not monitored_machins[instance.instance_type]:
                instance.id.start()
                turned_off.remove(instance)
        c.release()


class PricingThread(threading.Thread):

    def __init__(self, ths, instance_types, region, client, instances):
        threading.Thread.__init__(self)
        self.ths = ths
        self.instance_types = instance_types
        self.region = region
        self.client = client
        self.instances = instances

    def run(self):
        while True:
            prices = self.client.describe_spot_price_history(self.instance_types, len(self.instances), self.region)

            c.acquire()
            for i in len(prices):
                if prices['SpotPriceHistory'][i] >= self.ths:
                    monitored_machines[prices['InstanceType'][i]] = True
                else:
                    monitored_machines[prices['InstanceType'][i]] = False
            c.notifyAll()
            c.release()


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Wrong input, please attach maximum biding price")
        exit(1)

    monitor(sys.argv[1])


