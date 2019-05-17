#### 项目简介

此项目主要用来调用360公司私有云团队的wayne项目后台接口, 用于通过命令行方式快速创建项目在wayne中对应部署, 负载均衡, 以及ingress. 

#### 环境说明

python2.7.10
docker 18.09.6

*注意, 此脚本目前只支持ldap用户认证, wayne本地用户认证暂支持*

#### 使用方式

* docker build ./ -t IMAGE:TAG
* 修改本仓库下面的.env文件中对应的配置
* docker run  --rm --env-file .env IMAGE:TAG wayne_tools.py --namespace ns3 --app_name APP_NAME --project_name PROJECT_NAME \
   --image IMAGE --k8s_cluser_name K8S_CLUSTER_NAME --debug true

#### 参数说明

* --namespace: 为k8s中的namespace名称空间. *此namespace值必须与wayne中的命名空间值相同*
* --app_name: 对应wayne中的项目名
* --project_name: 项目名称, 代码仓库名称
* --image: 需要发布的docker镜像名称
* --k8s_cluser_name: wayne中添加的k8s集群名称
* --debug: 是否开启debug模式 (true为开启debug模式)


#### 鸣谢

感谢@360公司私有云团队wayne项目的所有开发人员. 
