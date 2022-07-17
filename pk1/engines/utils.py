def remedy_scale_ambari_bootstrap():
    return "sed -i 's/hostname=localhost/hostname=master1.packone/g' /etc/ambari-agent/conf/ambari-agent.ini\n\n" \
        "ambari-agent start >/dev/null 2>&1\n\n" \
        'if [ `hostname` == "master1.packone" ]; then\n' \
        'yum -q -y install epel-release 2>/dev/null\n' \
        'yum -q -y install python-pip 2>/dev/null\n' \
        'pip --disable-pip-version-check install ambari\n' \
        "fi\n\n" \
        'if [ `hostname` == "master1.packone" ]; then\n' \
        'sleep 15\n' \
        'ambari localhost:8080 cluster create packone typical_triple master1.packone master2.packone slave.packone\n' \
        "fi"

def remedy_scale_ambari_fast_init():
    return 'rm -rf /hadoop\n' \
        'mkdir -p /data/hadoop\n' \
        'ln -sf /data/hadoop /hadoop\n' \
        '#env\n' \
        "echo 'JAVA_HOME=/usr/jdk64/default'>>/etc/profile.d/packone-java.sh\n" \
        "echo 'JRE_HOME=/usr/jdk64/default/jre'>>/etc/profile.d/packone-java.sh\n" \
        "echo 'CLASS_PATH=.:$JAVA_HOME/lib:$JRE_HOME/lib'>>/etc/profile.d/packone-java.sh\n" \
        "echo 'PATH=$JAVA_HOME/bin:$JRE_HOME/bin:$PATH'>>/etc/profile.d/packone-java.sh\n" \
        'reboot\n' \
        'if [ `hostname` == "master1.packone" ]; then\n' \
        '    sleep 60\n' \
        '    pip --disable-pip-version-check install ambari\n' \
        '    ambari master1.packone:8080 service start\n' \
        'fi\n' \

def remedy_scale_ambari_fast_scale_out():
    return "rm -rf /hadoop\n" \
        "mkdir -p /data/hadoop\n" \
        "ln -sf /data/hadoop /hadoop\n" \
        "#env\n" \
        "echo 'JAVA_HOME=/usr/jdk64/default'>>/etc/profile.d/packone-java.sh\n" \
        "echo 'JRE_HOME=/usr/jdk64/default/jre'>>/etc/profile.d/packone-java.sh\n" \
        "echo 'CLASS_PATH=.:$JAVA_HOME/lib:$JRE_HOME/lib'>>/etc/profile.d/packone-java.sh\n" \
        "echo 'PATH=$JAVA_HOME/bin:$JRE_HOME/bin:$PATH'>>/etc/profile.d/packone-java.sh\n" \
        "reboot\n" \
        "pip --disable-pip-version-check install ambari\n" \
        "ambari master1.packone:8080 host clone slave.packone `hostname`\n" \

def remedy_scale_ambari_fast_scale_in():
    return '#ambari master1.packone:8080 host delete `hostname`'