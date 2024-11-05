package com.sanda.cname.controller;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseBody;

import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.List;
import java.util.Random;

@Controller
public class NameController {

    @GetMapping("/")
    public String index() {
        return "index";
    }

    @PostMapping("/submit-name")
    @ResponseBody
    public String submitName(@RequestParam("name") String name) {
        try (FileWriter fileWriter = new FileWriter("names.txt", true);
             PrintWriter printWriter = new PrintWriter(fileWriter)) {
            printWriter.println(name);
        } catch (IOException e) {
            e.printStackTrace();
            return "提交失败！";
        }
        return "姓名已成功提交！";
    }
    @GetMapping("/pick-random-name")
    @ResponseBody
    public String pickRandomName() {
        try {
            List<String> names = Files.readAllLines(Paths.get("names.txt"));
            if (names.isEmpty()) {
                return "没有名字可供抽取！";
            }
            Random random = new Random();
            String randomName = names.get(random.nextInt(names.size()));
            return randomName;
        } catch (IOException e) {
            e.printStackTrace();
            return "读取失败！";
        }
    }
}