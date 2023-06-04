import tomllib
from datetime import datetime

import ovh
import whatismyip as whatismyip


def main():
    with open("./conf.toml", "rb") as conf_file:
        conf = tomllib.load(conf_file)
    client = ovh.Client(
        **conf["ovh"]
    )

    result = client.get("/domain/zone/{zoneName}/record?subDomain={subdomain}&fieldType=A".format(**conf["dns"]))
    match len(result):
        case 0:
            raise RuntimeError("No zones found for {subdomain}.{zoneName}".format(**conf["dns"]))
        case 1:
            zone_id = result[0]
        case _:
            raise RuntimeError("Too many zones found for {subdomain}.{zoneName}".format(**conf["dns"]))

    zone_url = "/domain/zone/{zoneName}/record/{zone_id}".format(**conf["dns"], zone_id=zone_id)
    target = client.get(zone_url)["target"]
    current_ip = whatismyip.whatismyipv4()
    if target != current_ip:
        print(f"{datetime.now().isoformat()} - {target} != {current_ip}; upgrading")
        client.put(zone_url, target=current_ip, subDomain=conf["dns"]["subdomain"], ttl=conf["dns"]["ttl"])
    else:
        print(f"{datetime.now().isoformat()} - zone correctly points to {current_ip}")


if __name__ == '__main__':
    main()
