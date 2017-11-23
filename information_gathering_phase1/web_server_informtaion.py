# SWAMI KARUPPASWAMI THUNNAI

import socket
from url.URL import URL
import requests
from concurrent.futures import ThreadPoolExecutor
from information_gathering_phase1.firewall_info import FirewallInformation
from threading import Thread
from information_gathering_phase1.database import InfoGatheringPhaseOneDatabase


class WebServerInformation(FirewallInformation, InfoGatheringPhaseOneDatabase):
    """
    Description:
    =============
    This class is used to used to
    get some valuable information about the webserver
    Information gathered:
    =======================
    1. Web-Server Name, e.g Apache
    2. Remote Host Os, e.g Windows
    3. Programming Language Used, e.g PHP
    4. Presence of firewall like Cloudflare
    """
    __project_id = 0
    __connection = None
    __thread_semaphore = None
    __database_semaphore = None
    __url = None
    __ip = None
    __firewall = None
    __webserver_name = None
    __webserver_os = None
    __programming_language_used = None

    def __init__(self, project_id, connection, thread_semaphore, database_semaphore, url):
        """
        Paramters:
        ==========
        :param thread_semaphore: This semaphore is used to control the running threads
        :param database_semaphore: This semaphore is used to add control the threads which
        adds information to the database
        :param url: The url for which the information is to be gathered
        :param connection: MySQL database connection object
        :return: None
        """
        self.__project_id = project_id
        self.__connection = connection
        self.__thread_semaphore = thread_semaphore
        self.__database_semaphore = database_semaphore
        self.__url = url
        # get the ip address of the url
        with ThreadPoolExecutor(max_workers=1) as executor:
            ip = executor.submit(URL().get_ip, self.__url)
            self.__ip = ip.result()

    def __check_for_firewall(self):
        """
        This method will check if any firewall is present or Not
        :return:
        """
        self.__thread_semaphore.acquire()
        self.__firewall = FirewallInformation().get_info(url=self.__url, ip=self.__ip)
        self.__thread_semaphore.release()

    def __get_server_header(self):
        """
        This method is used to get the server header by sending a
        request to the bad gateway
        :return:
        """
        self.__thread_semaphore.acquire()
        try:
            tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_socket.connect((self.__ip, 80))  # connect to http port no 80
            tcp_socket.send("GET / HTTP/1.1\r\n\r\n".encode("utf-8"))
            result = tcp_socket.recv(4096)  # receive first 4096 bytes of information
            result = result.decode("utf-8")
            result = result.split("\r\n")
            for i in result:
                if "Server" in i:
                    i = i.replace("Server:", "")
                    i = i.strip()
                    self.__webserver_name = i  # we have obtained the server name
        except socket.error as e:
            print(e)
        except TypeError as e:
            print(e)
        finally:
            self.__thread_semaphore.release()

    def __get_programming_language(self):
        """
        We will use to get the programming language from the session ID
        :return:
        """
        self.__thread_semaphore.acquire()
        r = URL().get_request(url=self.__url)
        cookies = r.cookies if r is not None else ""
        session_id = requests.utils.dict_from_cookiejar(cookies)
        # session_id contains the session id of the targetted url
        if "PHPSESSID" in session_id:
            self.__programming_language_used="PHP"
        elif "JSESSIONID" in session_id:
            self.__programming_language_used = "J2EE"
        elif "ASP.NET_SessionId" in session_id:
            self.__programming_language_used = "ASP.NET"
        elif "CFID & CFTOKEN" in session_id:
            self.__programming_language_used = "COLDFUSION"
        else:
            self.__programming_language_used = "None"
        self.__thread_semaphore.release()

    def gather_information(self):
        """
        This method is used to gather all the webserver information
        :return: None
        """
        # By now we have obtained the url and the I.P address of the website
        # Now scan for firewalls
        if self.__ip is not None:
            firewall_check = Thread(target=self.__check_for_firewall)
            firewall_check.start()
            firewall_check.join()
            # self.__firwall now has the name of the firewall if present
        """
        @ This stage we have acquired self.__url, self.__ip and self.__firewall
        """
        if self.__firewall is None:
            server_name = Thread(target=self.__get_server_header)
            server_name.start()
            server_name.join()
            # Now we have the web server name
        # Now get the web server os
        if self.__webserver_name is not None:
            self.__webserver_os = "Windows" if "Win" in self.__webserver_name else "Unix/Liux"
        # Now get the programming language
        programming_lang = Thread(target=self.__get_programming_language)
        programming_lang.start()
        programming_lang.join()
        # Now let us see what we have got
        print("IP:       ", self.__ip)
        print("DOMAIN:   ", URL().get_host_name(self.__url))
        print("SERVER:   ", self.__webserver_name)
        print("OS:       ", self.__webserver_os)
        print("Firewall: ", self.__firewall)
        print("Language: ", self.__programming_language_used)
        if self.__ip is None:
            self.__ip = "None"
        if self.__webserver_name is None:
            self.__webserver_name = "None"
        if self.__webserver_os is None:
            self.__webserver_os = "None"
        if self.__programming_language_used is None:
            self.__programming_language_used = "None"
        if self.__firewall is None:
            self.__firewall = "None"
        # Now add the information to database
        query = "insert into info_gathering values(%s,%s,%s,%s,%s,%s,%s)"
        args = (self.__project_id, "PRELIMINARY", self.__ip, self.__webserver_name,
                              self.__webserver_os, self.__programming_language_used,
                              self.__firewall)
        # A thread to add the information to the database
        database_adding_thread = Thread(target=self.add_info_gathering_phase_one, args=(self.__database_semaphore, self.__connection, query, args))
        database_adding_thread.start()
        database_adding_thread.join()
