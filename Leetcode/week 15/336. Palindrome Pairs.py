import collections
from typing import *

class TrieNode:
    def __init__(self):
        self.children = collections.defaultdict(TrieNode)
        self.word_id = -1
        self.palindrome_word_ids = []

class Trie:
    def __init__(self):
        self.root = TrieNode()

    @staticmethod # 클래스와 독립적으로 함수로서의 의미, 즉 클래스 바깥에 함수를 별도로 선언한 것과 같은 의미.
    def is_palindrome(word: str) -> bool:
        return word[::] == word [::-1]

  #단어 삽입 메소드
    def insert(self, index, word) -> None:
        node = self.root
        for i, char in enumerate(reversed(word)):
            if self.is_palindrome(word[0:len(word) - i]):
                node.palindrome_word_ids.append(index)
            node = node.children[char]
            node.val = char
        node.word_id = index

    def search(self, index, word) -> List[List[int]]:
        result = []
        node = self.root

        while word:
            # 판별 로직 3
            if node.word_id >= 0:
                if self.is_palindrome(word):
                    result.append([index,node.word_id])
            if not word[0] in node.children:
                return result
            node = node.children[word[0]]
            word = word[1:]

        # 판별 로직 1
        if node.word_id >= 0 and node.word_id != index:
            result.append([index,node.word_id])

        # 판별 로직 2
        for palindrome_word_id in node.palindrome_word_ids:
            result.append([index, palindrome_word_id])

        return result

class Solution:
    def palindromePairs(self, words: List[str]) -> List[List[int]]:
        trie = Trie()

        for i, word in enumerate(words):
            trie.insert(i,word)

        results = []
        for i, word in enumerate(words):
            results.extend(trie.search(i,word))

        return results