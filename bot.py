import board
import random
import math

# chars for table values
PLAYER_CHAR = '0'			# player
ENEMY_CHAR = '1'			# opponent
EMPTY_CHAR = ' '			# empty space

# factor weights for evaluation
LINE_WEIGHT = 1				# line scores
CENTRALITY_WEIGHT = 8		# central control

# infinite values
MAX_VAL = math.inf			# positive infinity
MIN_VAL = -math.inf			# negative infinity


# calculate current node score
def getCurrScore(prevScore, state):
	score = prevScore

	# win, draw and loss 
	if state.checkWin():
		if state.lastPlay[2] == PLAYER_CHAR:
			return MAX_VAL
		else:
			return MIN_VAL
	
	if state.checkFull():
		return 0

	# correct score based on lines affected by last play

	# finds line score for a line
	def evaluateLine(line):
		# find base score of player advantage
		lineScore = 0

		# score for connected sequences
		playerCount = 0
		enemyCount = 0
		totalLen = 0
		prevChar = EMPTY_CHAR

		for i in range(len(line)):
			totalLen += 1
			if line[i] == PLAYER_CHAR: playerCount += 1
			elif line[i] == ENEMY_CHAR: enemyCount += 1

			if totalLen > state.winNum:
				if prevChar == PLAYER_CHAR: playerCount -= 1
				elif prevChar == ENEMY_CHAR: enemyCount += 1
				prevChar = line[i+1-totalLen]

			lineScore += playerCount - enemyCount
			
			if enemyCount == 0:
				lineScore += playerCount**2
			
			if playerCount == 0:
				lineScore -= enemyCount**2
		
		return lineScore*LINE_WEIGHT

	# position of last play counter
	midRow = state.lastPlay[0]
	midCol = state.lastPlay[1]

	# starting row and columns for directions
	rStart = max(0, midRow-midCol)
	cStart = max(0, midCol-midRow)

	# holds all lines affected by last play
	directions = []

	# horizontal
	curr = []
	for col in range(state.numColumns):
		curr.append(state.checkSpace(midRow, col).value)
	directions.append(curr)

	# vertical
	curr = []
	for row in range(state.numRows):
		curr.append(state.checkSpace(row, midCol).value)
	directions.append(curr)

	# diagonal (+ gradient)
	curr = []
	for i in range(min(state.numRows-rStart, state.numColumns-cStart)):
		curr.append(state.checkSpace(rStart+i, cStart+i).value)
	directions.append(curr)	
	
	# diagonal (- gradient)
	curr = []
	for i in range(min(state.numRows-rStart, state.numColumns-cStart)):
		curr.append(state.checkSpace(state.numRows-rStart-i-1, cStart+i).value)
	directions.append(curr)	

	# calculate new scores for lines 
	for line in directions:
		score += evaluateLine(line)
	
	# calculate previous scores for lines
		
	# undo last move
	directions[0][midCol] = EMPTY_CHAR
	directions[1][midRow] = EMPTY_CHAR
	directions[2][min(midRow, midCol)] = EMPTY_CHAR
	directions[3][min(midRow, midCol)] = EMPTY_CHAR

	for line in directions:
		score -= evaluateLine(line)

	# centrality
	wnToBS = ((state.winNum**2)/(state.numRows*state.numColumns))
	cen = state.numRows - abs((state.numRows//2) - midRow) + state.numColumns - abs((state.numColumns//2) - midCol) * wnToBS * CENTRALITY_WEIGHT
	
	if state.lastPlay[2] == PLAYER_CHAR: score += cen
	elif state.lastPlay == ENEMY_CHAR: score -= cen

	return score


# game tree node
class Node:

	def __init__(self, isMaximising, currState, prevScore):
		self.isMaximising = isMaximising
		self.children = None
		self.bestMove = -1
		self.pruneCount = 0
		self.currScore = getCurrScore(prevScore, currState)
		self.isOver = currState.checkWin() or currState.checkFull()


	# gets character to play 
	def getChar(self):
		if self.isMaximising:
			return PLAYER_CHAR
		else:
			return ENEMY_CHAR
	

	# gets default evaluation value
	def getDefaultEval(self):
		if self.isMaximising:
			return MIN_VAL
		else:
			return MAX_VAL
	

	# get new evalInfo and bestMoves
	def getNewEval(self, evalInfo, childInfo, bestMoves, col):
	
		if evalInfo[0] == None or not evalInfo[2]:
			evalInfo = childInfo
			bestMoves = [col]

		if childInfo[2]:
			if self.isMaximising:
				# better eval score
				if childInfo[0] > evalInfo[0]:
					evalInfo = childInfo
					bestMoves = [col]
				# same eval score
				elif childInfo[0] == evalInfo[0]:
					# if depth smaller and eval positive
					if childInfo[1] < evalInfo[1] and evalInfo[0] > 0:
						evalInfo = childInfo
						bestMoves = [col]
					# depth equal
					elif childInfo[1] == evalInfo[1]:
						bestMoves.append(col)
					# if depth greater and eval negative
					elif childInfo[1] > evalInfo[1] and evalInfo[0] < 0:
						evalInfo = childInfo
						bestMoves = [col]
			else:
				# better eval score
				if childInfo[0] < evalInfo[0]:
					evalInfo = childInfo
					bestMoves = [col]
				# same eval score
				elif childInfo[0] == evalInfo[0]:
					# if depth smaller and eval negative
					if childInfo[1] < evalInfo[1] and evalInfo[0] < 0:
						evalInfo = childInfo
						bestMoves = [col]
					# depth equal
					elif childInfo[1] == evalInfo[1]:
						bestMoves.append(col)
					# if depth greater and eval positive
					elif childInfo[1] > evalInfo[1] and evalInfo[0] > 0:
						evalInfo = childInfo
						bestMoves = [col]

		return evalInfo, bestMoves


	# DFS for evaluation and best move (no pruning)
	def evaluate(self, depth, currState):
		# if game over or depth reached, evaluate and do not check further moves
		if self.isOver or depth == 0:
			return self.currScore, 0
		
		# consider future moves
		evalInfo = (None, MAX_VAL, False)		# score, depth, valid
		bestMoves = []							# moves to choose from

		if not self.children:
			self.children = []

		# iterate through children
		for i in range(currState.numColumns):
			# calculate child board state
			moveValid = currState.addPiece(i, self.getChar())

			# if child does not exist, create it
			if i >= len(self.children):	
				if moveValid or not self.isMaximising:
					newNode = Node(not self.isMaximising, currState, self.currScore)
					self.children.append(newNode)			
				else:
					self.children.append(None)

			# evaluate child and compare
			child = self.children[i]
			if child:
				childEval, childDepth = child.evaluate(depth-1, currState)

				# perform evaluation against existing values
				evalInfo, bestMoves = self.getNewEval(evalInfo, (childEval, childDepth, moveValid), bestMoves, i)

			# restore previous board state
			if moveValid: currState.removePiece(i)

		# find best move
		self.bestMove = random.choice(bestMoves)

		return evalInfo[0], evalInfo[1]+1


	# returns indexes of children in most promising order
	def orderChildren(self):
		# remove invalid children
		indices = [i for i, child in enumerate(self.children) if child is not None]
		# order by node eval score
		indices.sort(key=lambda i: self.children[i].currScore, reverse=self.isMaximising)

		return indices
	

	# DFS for evaluation and best move (alpha-beta pruning)
	def abEvaluate(self, depth, a, b, currState):
		# reset prune count
		self.pruneCount = 0

		# if game over or depth reached, evaluate and do not check further moves
		if self.isOver or depth == 0:
			return self.currScore, 0

		# otherwise, consider future moves
		evalInfo = (None, MAX_VAL, False)		# score, depth, valid
		bestMoves = []							# moves to choose from

		# check existing children
		if self.children:
			# iterate through ordered children
			for col in self.orderChildren():
				child = self.children[col]

				# evaluate and compare
				moveValid = currState.addPiece(col, self.getChar())
				
				childEval, childDepth = child.abEvaluate(depth-1, a, b, currState)
				self.pruneCount += child.pruneCount
				evalInfo, bestMoves = self.getNewEval(evalInfo, (childEval, childDepth, moveValid), bestMoves, col)

				if moveValid: currState.removePiece(col)

				# pruning check
				prune = False
				if moveValid:
					if self.isMaximising:
						# beta prune
						if childEval >= b:
							prune = True
						a = max(a, childEval)
					else:
						# alpha prune
						if childEval <= a:
							prune = True
						b = min(b, childEval)

				if prune:
					self.pruneCount += 1
					self.bestMove = random.choice(bestMoves)
					return evalInfo[0], evalInfo[1]+1

		else:
			self.children = []

		# check children that do not exist yet
		for col in range(len(self.children), currState.numColumns):
			moveValid = currState.addPiece(col, self.getChar())

			if moveValid or not self.isMaximising:
				# create child
				child = Node(not self.isMaximising, currState, self.currScore)
				self.children.append(child)

				# evaluate and compare
				childEval, childDepth = child.abEvaluate(depth-1, a, b, currState)
				self.pruneCount += child.pruneCount
				evalInfo, bestMoves = self.getNewEval(evalInfo, (childEval, childDepth, moveValid), bestMoves, col)

				if moveValid: currState.removePiece(col)

				# pruning check
				prune = False
				if moveValid:
					if self.isMaximising:
						# beta prune
						if childEval >= b:
							prune = True
						a = max(a, childEval)
					else:
						# alpha prune
						if childEval <= a:
							prune = True
						b = min(b, childEval)

				if prune:
					self.pruneCount += 1
					self.bestMove = random.choice(bestMoves)
					return evalInfo[0], evalInfo[1]+1				

			# move invalid and player maximising so don't expand (will never be explored)
			else:
				self.children.append(None)
		
		# find best move
		self.bestMove = random.choice(bestMoves)

		return evalInfo[0], evalInfo[1]+1


	# perform all required actions for a turn (called on root node)
	def takeTurn(self, depth, isAB, currState):

		if isAB:
			# evaluate position with alpha-beta pruning
			_ = self.abEvaluate(depth, a=MIN_VAL, b=MAX_VAL, currState=currState)
		else:
			# evaluate position with no pruning
			_ = self.evaluate(depth, currState)
		
		return self.bestMove


	# get node representing next move
	def moveTo(self, move, currState):
		# find new board state
		_ = currState.addPiece(move, self.getChar())

		# branch pruned
		if move >= len(self.children):
			# create node and return
			return Node(not self.isMaximising, currState, self.currScore), currState
		
		# node exists
		else:
			return self.children[move], currState
	

	# count node descendants
	def countDesc(self):
		count = 0
		if self.children:
			for child in self.children:
				if child:
					count += child.countDesc() + 1
		return count


# change the board so names are now known chars
def convertBoard(gameBoard, name):
	# copy board
	newBoard = gameBoard.copy()
	# alter entries
	for row in range(newBoard.numRows):
		for col in range(newBoard.numColumns):
			curr = newBoard.checkSpace(row, col).value

			if curr == name:
				newBoard.gameBoard[row][col].value = PLAYER_CHAR
			elif curr != EMPTY_CHAR:
				newBoard.gameBoard[row][col].value = ENEMY_CHAR

	# if player took last turn
	if newBoard.lastPlay[2] == name:
		newBoard.lastPlay[2] = PLAYER_CHAR
	# if enemy has taken last turn
	elif newBoard.lastPlay[0] != -1:
		newBoard.lastPlay[2] = ENEMY_CHAR

	# newBoard.printBoard()
	return newBoard


# find optimal max search depth
def getMaxDepth(gameBoard):
	# count the number of filled spaces
	numFull = 0
	for count in gameBoard.colFills:
		numFull += count
	
	# get the proportion of filled spaces 
	fracFull = numFull/(gameBoard.numColumns*gameBoard.numRows)

	# evaluate proportion to find ideal recursion depth
	if fracFull < (gameBoard.winNum-2)/(gameBoard.winNum-1):
		return 4
	else:
		return 6

# Connect player
class Player:
	
	def __init__(self, name):
		self.name = name
		self.numExpanded = 0	# number of nodes expanded
		self.numPruned = 0		# number of times a branch is pruned

		self.root = None		# game tree root node
		self.currState = None	# root node board state
	

	# complete actions for the turn
	def turn(self, gameBoard, isAB):
		# max search depth
		maxDepth = getMaxDepth(gameBoard)
		
		# find current node

		# player has first move
		if self.root == None and self.currState == None and gameBoard.lastPlay[0] == -1:
			self.root = Node(True, gameBoard, 0)
			self.currState = gameBoard
		
		# player starts on second move
		elif self.root == None:
			# convert any existing names to known chars
			newBoard = convertBoard(gameBoard, self.name)
			self.root = Node(True, newBoard, 0)
			self.currState = newBoard
		
		# all later moves
		else:
			# find new enemy move and traverse tree to new position
			self.root, self.currState = self.root.moveTo(gameBoard.lastPlay[1], self.currState)
		
		# take the turn
		prevDescCount = self.root.countDesc()
		move = self.root.takeTurn(maxDepth, isAB, self.currState)
		newDescCount = self.root.countDesc()
		self.numExpanded += newDescCount - prevDescCount
		self.numPruned += self.root.pruneCount

		# traverse tree according to move
		self.root, self.currState = self.root.moveTo(move, self.currState)

		return move
	

	# find next move without alpha-beta pruning
	def getMove(self, gameBoard):
		return self.turn(gameBoard, False)


	# find next move with alpha-beta pruning
	def getMoveAlphaBeta(self, gameBoard):
		return self.turn(gameBoard, True)