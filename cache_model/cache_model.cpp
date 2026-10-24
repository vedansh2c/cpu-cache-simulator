// Original set-associative, write-agnostic address-only cache with exact LRU.
#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <list>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

static uint64_t number(const std::string &text) {
    if (text.empty() || text[0] == '-') throw std::invalid_argument("invalid unsigned integer");
    size_t used = 0;
    uint64_t value = std::stoull(text, &used, text.starts_with("0x") ? 16 : 10);
    if (used != text.size()) throw std::invalid_argument("invalid integer suffix");
    return value;
}
static bool power_two(uint64_t value) { return value && !(value & (value - 1)); }

int main(int argc, char **argv) {
    try {
        if (argc != 5) throw std::invalid_argument("usage: cache_model CAPACITY_BYTES BLOCK_BYTES WAYS TRACE");
        uint64_t capacity = number(argv[1]), block = number(argv[2]), ways = number(argv[3]);
        if (!power_two(capacity) || !power_two(block) || !power_two(ways)
            || capacity > 64*1024*1024 || block > capacity || ways > capacity/block)
            throw std::invalid_argument("invalid cache geometry (maximum capacity 64 MiB)");
        uint64_t sets = capacity / block / ways;
        if (!power_two(sets)) throw std::invalid_argument("set count must be a power of two");
        std::vector<std::list<uint64_t>> lines(sets);
        std::ifstream trace(argv[4]);
        if (!trace) throw std::runtime_error("cannot open trace");
        std::string line;
        uint64_t hits = 0, misses = 0;
        while (std::getline(trace, line)) {
            line = line.substr(0, line.find('#'));
            std::istringstream stream(line);
            std::string token, extra;
            if (!(stream >> token)) continue;
            if (stream >> extra) throw std::invalid_argument("one address per trace line required");
            uint64_t address = number(token), tag = address/block;
            auto &set = lines[tag%sets];
            auto found = std::find(set.begin(), set.end(), tag);
            if (found == set.end()) {
                ++misses;
                if (set.size() == ways) set.pop_back();
            } else { ++hits; set.erase(found); }
            set.push_front(tag);
        }
        if (trace.bad()) throw std::runtime_error("trace read failed");
        std::cout << "{\"accesses\":" << hits+misses << ",\"hits\":" << hits
                  << ",\"misses\":" << misses << ",\"miss_rate\":";
        if (hits+misses) std::cout << double(misses)/(hits+misses);
        else std::cout << "null";
        std::cout << "}\n";
        return 0;
    } catch (const std::exception &error) {
        std::cerr << error.what() << '\n';
        return 2;
    }
}
